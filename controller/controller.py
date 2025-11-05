import aiohttp
import asyncio
import time
import json
import logging
import sys

# --- Configuração do Logging ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    stream=sys.stdout,
)

# --- Constantes ---
ISSUER_ADMIN = "http://localhost:8001"
HOLDER_ADMIN = "http://localhost:8011"
VERIFIER_ADMIN = "http://localhost:8021"

SCHEMA_NAME = "diploma_schema"
SCHEMA_VERSION = "1.0"
SCHEMA_ATTRIBUTES = ["nome", "curso", "data_formatura"]


async def wait_for_agent(session, admin_url, label):
    """Espera o agente ficar pronto."""
    logging.info(f"Aguardando {label} em {admin_url}...")
    while True:
        try:
            async with session.get(f"{admin_url}/status") as resp:
                if resp.status == 200:
                    logging.info(f"{label} está pronto!")
                    return
        except aiohttp.ClientConnectorError:
            pass
        await asyncio.sleep(2)


async def get_public_did(session, admin_url):
    """Obtém o DID público auto-provisionado do Issuer."""
    logging.info("Obtendo DID público do Issuer (criado via --auto-provision)...")
    max_retries = 10
    for i in range(max_retries):
        try:
            async with session.get(f"{admin_url}/wallet/did/public") as resp:
                if resp.status == 200:
                    did_info = await resp.json()
                    public_did = did_info.get("result", {}).get("did")
                    if public_did:
                        logging.info(f"DID Público do Issuer: {public_did}")
                        return public_did
                    else:
                        logging.warning(
                            f"Agente pronto, mas DID público ainda não disponível. "
                            f"Tentando novamente... ({i+1}/{max_retries})"
                        )
                else:
                    logging.error(
                        f"Erro ao obter DID público (Status {resp.status}): {await resp.text()}"
                    )
            await asyncio.sleep(3)
        except aiohttp.ClientConnectorError as e:
            logging.warning(f"Erro de conexão ao obter DID: {e}. Tentando novamente...")
            await asyncio.sleep(3)

    logging.error("Não foi possível obter o DID público após várias tentativas.")
    raise Exception("Falha ao obter DID Público do Issuer.")


async def create_schema_and_cred_def(session, public_did):
    """Cria um Schema e uma Credential Definition usando a API /anoncreds/."""
    
    # 1. Criar Schema
    logging.info("Criando Schema (API askar-anoncreds)...")
    
    schema_definition = {
        "issuerId": public_did,
        "name": SCHEMA_NAME,
        "version": SCHEMA_VERSION,
        "attrNames": SCHEMA_ATTRIBUTES
    }
    payload = {"schema": schema_definition}
    
    async with session.post(f"{ISSUER_ADMIN}/anoncreds/schema", json=payload) as resp:
        if resp.status != 200:
            logging.error(f"Erro ao criar schema (Status {resp.status}): {await resp.text()}")
            raise Exception("Falha ao criar Schema.")
            
        schema_result = await resp.json()
        
        # --- CORREÇÃO APLICADA AQUI ---
        # O ID vem de 'schema_state', não 'schema'
        schema_id = schema_result.get("schema_state", {}).get("schema_id")
        
        if not schema_id:
            logging.error(f"Erro: Resposta inesperada ao criar schema: {schema_result}")
            raise Exception("Falha ao extrair schema_id da resposta.")
            
        logging.info(f"Schema ID: {schema_id}")

    # 2. Criar Credential Definition
    logging.info("Criando Credential Definition (API askar-anoncreds)...")
    
    cred_def_definition = {
        "issuerId": public_did,
        "schemaId": schema_id,
        "tag": "default",
        "support_revocation": False
    }
    payload = {"credential_definition": cred_def_definition}
    
    async with session.post(f"{ISSUER_ADMIN}/anoncreds/credential-definition", json=payload) as resp:
        if resp.status != 200:
            logging.error(f"Erro ao criar CredDef (Status {resp.status}): {await resp.text()}")
            raise Exception("Falha ao criar Credential Definition.")
            
        cred_def_result = await resp.json()

        # --- CORREÇÃO (PROATIVA) APLICADA AQUI ---
        # O ID vem de 'credential_definition_state', não 'credential_definition'
        cred_def_id = cred_def_result.get("credential_definition_state", {}).get("credential_definition_id")

        if not cred_def_id:
            logging.error(f"Erro: Resposta inesperada ao criar CredDef: {cred_def_result}")
            raise Exception("Falha ao extrair cred_def_id da resposta.")
            
        logging.info(f"Credential Definition ID: {cred_def_id}")
        return cred_def_id


async def create_connection(session):
    """Cria e estabelece uma conexão entre Issuer e Holder."""
    
    logging.info("Issuer criando convite...")
    try:
        async with session.post(f"{ISSUER_ADMIN}/connections/create-invitation") as resp:
            resp.raise_for_status()
            invite = await resp.json()
    except aiohttp.ClientError as e:
        logging.error(f"Erro ao criar convite: {e}")
        raise
        
    invitation_details = invite["invitation"]
    connection_id_issuer = invite["connection_id"]
    logging.info("Convite criado pelo Issuer.")

    logging.info("Holder recebendo convite...")
    try:
        async with session.post(f"{HOLDER_ADMIN}/connections/receive-invitation", json=invitation_details) as resp:
            resp.raise_for_status()
            connection_holder = await resp.json()
    except aiohttp.ClientError as e:
        logging.error(f"Erro ao receber convite: {e}")
        raise
        
    connection_id_holder = connection_holder["connection_id"]

    logging.info("Aguardando conexão ficar ativa (auto-accept)...")
    while True:
        await asyncio.sleep(2)
        try:
            async with session.get(f"{ISSUER_ADMIN}/connections/{connection_id_issuer}") as resp:
                conn_issuer = await resp.json()
            if conn_issuer.get("state") == "active":
                logging.info("Conexão do Issuer ATIVA!")
                async with session.get(f"{HOLDER_ADMIN}/connections/{connection_id_holder}") as resp:
                    conn_holder = await resp.json()
                if conn_holder.get("state") == "active":
                    logging.info("Conexão do Holder ATIVA!")
                    return connection_id_issuer, connection_id_holder
        except aiohttp.ClientError as e:
            logging.warning(f"Erro ao verificar status da conexão: {e}. Tentando novamente...")

    logging.error("Falha ao estabelecer conexão após o convite.")
    raise Exception("Falha ao estabelecer conexão.")


async def issue_credential(session, connection_id_issuer, cred_def_id):
    """Issuer emite uma credencial para o Holder usando a API 2.0."""
    
    logging.info("Emitindo credencial de Diploma (API 2.0)...")
    
    issue_body = {
        "connection_id": connection_id_issuer,
        "comment": "Parabéns pelo seu diploma!",
        "filter": {
            "anoncreds": {  
                "cred_def_id": cred_def_id
            }
        },
        "credential_preview": {
            "@type": "issue-credential/2.0/credential-preview",
            "attributes": [
                {"name": "nome", "value": "Alice Silva"},
                {"name": "curso", "value": "Ciência da Computação"},
                {"name": "data_formatura", "value": "2025-10-28"}
            ]
        }
    }
    
    try:
        async with session.post(f"{ISSUER_ADMIN}/issue-credential-2.0/send", json=issue_body) as resp:
            resp.raise_for_status()
            issue_result = await resp.json()
            logging.info(f"Credencial emitida (state: {issue_result.get('state')}).")
    except aiohttp.ClientError as e:
        logging.error(f"Erro ao emitir credencial: {e}")
        raise
        
    logging.info("Holder deve receber e armazenar a credencial automaticamente.")

    
async def main():
    """Função principal do controlador."""
    async with aiohttp.ClientSession() as session:
        try:
            # 1. Espera os agentes
            await asyncio.gather(
                wait_for_agent(session, ISSUER_ADMIN, "Issuer"),
                wait_for_agent(session, HOLDER_ADMIN, "Holder"),
                wait_for_agent(session, VERIFIER_ADMIN, "Verifier")
            )
            logging.info("--- Todos os agentes estão online! ---")
            
            # 2. Issuer obtém DID público e cria Schema/CredDef
            public_did = await get_public_did(session, ISSUER_ADMIN)
            cred_def_id = await create_schema_and_cred_def(session, public_did)
            logging.info(f"--- Issuer pronto para emitir (CredDef: {cred_def_id}) ---")

            # 3. Conectar Issuer e Holder
            conn_id_issuer, conn_id_holder = await create_connection(session)
            logging.info(f"--- Conexão estabelecida (Issuer: {conn_id_issuer}, Holder: {conn_id_holder}) ---")
            
            # 4. Emitir Credencial
            await issue_credential(session, conn_id_issuer, cred_def_id)
            logging.info("--- Fluxo de Emissão Concluído ---")
            
        except Exception as e:
            logging.error(f"Uma falha crítica ocorreu: {e}")
            logging.error("O script será encerrado.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("\nParando o controlador (solicitado pelo usuário)...")