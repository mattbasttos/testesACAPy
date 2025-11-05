import aiohttp
import asyncio
import datetime
import time
import json
import os
from qrcode import QRCode

# --- URLs dos Agentes (do seu ambiente) ---
ISSUER_ADMIN = "http://localhost:8001"
HOLDER_ADMIN = "http://localhost:8011"
VERIFIER_ADMIN = "http://localhost:8021"

# --- Constantes do Script 'faber.py' ---
CRED_PREVIEW_TYPE = "https://didcomm.org/issue-credential/2.0/credential-preview"
CRED_FORMAT_ANONCREDS = "anoncreds"
CRED_FORMAT_VC_DI = "vc_di" # Adicionado para completude
CRED_FORMAT_JSON_LD = "json-ld" # Adicionado para completude
CRED_FORMAT_INDY = "indy" # Adicionado para completude
SIG_TYPE_BLS = "BbsBlsSignature2020" # Adicionado para completude

# Definições do Schema do 'faber.py' (Degree Schema)
SCHEMA_NAME = "degree schema"
SCHEMA_VERSION = "1.0"
SCHEMA_ATTRIBUTES = [
    "name",
    "date",
    "degree",
    "birthdate_dateint",
    "timestamp",
]

# --- Funções Auxiliares (recriadas do 'runners.support.utils') ---

def log_msg(message):
    """Imprime uma mensagem simples."""
    print(message)

def log_status(message):
    """Imprime uma mensagem de status formatada."""
    print(f"\n{message}\n")

async def prompt(prompt_string, default=None):
    """Gera um prompt de input e retorna a resposta."""
    if default:
        prompt_string = f"{prompt_string} [{default}]: "
    else:
        prompt_string = f"{prompt_string}: "
    
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, input, prompt_string) or default

async def prompt_loop(options):
    """Loop de prompt assíncrono."""
    loop = asyncio.get_event_loop()
    while True:
        try:
            val = await loop.run_in_executor(None, input, options)
            yield val
        except (KeyboardInterrupt, EOFError):
            yield None

# --- Funções de Lógica do Agente (adaptadas do seu 'controller.py') ---

async def wait_for_agent(session, admin_url, label):
    """Espera o agente ficar pronto."""
    log_status(f"Aguardando {label} em {admin_url}...")
    while True:
        try:
            async with session.get(f"{admin_url}/status") as resp:
                if resp.status == 200:
                    log_msg(f"{label} está pronto!")
                    break
        except aiohttp.ClientConnectorError:
            pass
        await asyncio.sleep(2)

async def get_public_did(session):
    """Obtém o DID público do Issuer."""
    log_status("Obtendo DID público do Issuer (criado via --auto-provision)...")
    max_retries = 10
    for i in range(max_retries):
        try:
            async with session.get(f"{ISSUER_ADMIN}/wallet/did/public") as resp:
                if resp.status == 200:
                    did_info = await resp.json()
                    public_did = did_info.get("result", {}).get("did")
                    if public_did:
                        log_msg(f"DID Público do Issuer: {public_did}")
                        return public_did
                log_msg(f"Agente pronto, mas DID público ainda não disponível. Tentando novamente...")
            await asyncio.sleep(3)
        except aiohttp.ClientConnectorError as e:
            log_msg(f"Erro de conexão: {e}. Tentando novamente...")
            await asyncio.sleep(3)
    log_msg("Erro: Não foi possível obter o DID público.")
    return None

async def create_schema_and_cred_def(session, public_did):
    """Cria o Schema e CredDef do 'faber.py'."""
    log_status("Criando Schema (API askar-anoncreds)...")
    
    schema_definition = {
        "issuer_id": public_did,
        "name": SCHEMA_NAME,
        "version": SCHEMA_VERSION,
        "attr_names": SCHEMA_ATTRIBUTES
    }
    payload = {"schema": schema_definition} 
    
    async with session.post(f"{ISSUER_ADMIN}/anoncreds/schema", json=payload) as resp:
        if resp.status != 200:
            log_msg(f"Erro ao criar schema: {await resp.text()}")
            return None
        schema_result = await resp.json()
        schema_id = schema_result.get("schema", {}).get("schema_id")
        log_msg(f"Schema ID: {schema_id}")

    log_status("Criando Credential Definition (API askar-anoncreds)...")
    cred_def_definition = {
        "issuer_id": public_did,
        "schema_id": schema_id,
        "tag": "default",
        "support_revocation": False # O script 'faber.py' suporta, mas seu run_issuer.py não
    }
    payload = {"credential_definition": cred_def_definition}
    
    async with session.post(f"{ISSUER_ADMIN}/anoncreds/credential-definition", json=payload) as resp:
        if resp.status != 200:
            log_msg(f"Erro ao criar CredDef: {await resp.text()}")
            return None
        cred_def_result = await resp.json()
        cred_def_id = cred_def_result.get("credential_definition", {}).get("credential_definition_id")
        log_msg(f"Credential Definition ID: {cred_def_id}")
        return cred_def_id

async def create_connection(session):
    """Cria uma conexão entre Issuer e Holder."""
    log_status("Issuer criando convite...")
    async with session.post(f"{ISSUER_ADMIN}/connections/create-invitation") as resp:
        invite = await resp.json()
    
    invitation_details = invite["invitation"]
    connection_id_issuer = invite["connection_id"]
    log_msg(f"Convite do Issuer: {json.dumps(invitation_details, indent=2)}")

    log_status("Holder recebendo convite...")
    async with session.post(f"{HOLDER_ADMIN}/connections/receive-invitation", json=invitation_details) as resp:
        connection_holder = await resp.json()
        connection_id_holder = connection_holder["connection_id"]

    log_status("Aguardando conexão ficar ativa (graças às flags 'auto-accept')...")
    while True:
        await asyncio.sleep(2)
        async with session.get(f"{ISSUER_ADMIN}/connections/{connection_id_issuer}") as resp:
            conn_issuer = await resp.json()
        if conn_issuer.get("state") == "active":
            log_msg("Conexão do Issuer ATIVA!")
            async with session.get(f"{HOLDER_ADMIN}/connections/{connection_id_holder}") as resp:
                conn_holder = await resp.json()
                if conn_holder.get("state") == "active":
                    log_msg("Conexão do Holder ATIVA!")
                    return connection_id_issuer, connection_id_holder
    return None, None

# --- Funções Geradoras de Payload (adaptadas do 'faber.py') ---

def generate_credential_offer(connection_id, cred_def_id, exchange_tracing):
    """Gera o payload da oferta de credencial."""
    age = 24
    d = datetime.date.today()
    birth_date = datetime.date(d.year - age, d.month, d.day)
    birth_date_format = "%Y%m%d"
    
    cred_attrs = {
        "name": "Alice Smith",
        "date": "2018-05-28",
        "degree": "Maths",
        "birthdate_dateint": birth_date.strftime(birth_date_format),
        "timestamp": str(int(time.time())),
    }

    cred_preview = {
        "@type": CRED_PREVIEW_TYPE,
        "attributes": [
            {"name": n, "value": v} for (n, v) in cred_attrs.items()
        ],
    }
    
    # Usando o formato askar-anoncreds que você está rodando
    _filter = {"anoncreds": {"cred_def_id": cred_def_id}}
    
    offer_request = {
        "connection_id": connection_id,
        "comment": f"Offer on cred def id {cred_def_id}",
        "auto_remove": False,
        "credential_preview": cred_preview,
        "filter": _filter,
        "trace": exchange_tracing,
    }
    return offer_request

def generate_proof_request(connection_id, exchange_tracing, connectionless=False):
    """Gera o payload do pedido de prova."""
    age = 18
    d = datetime.date.today()
    birth_date = datetime.date(d.year - age, d.month, d.day)
    birth_date_format = "%Y%m%d"

    req_attrs = [
        {"name": "name", "restrictions": [{"schema_name": SCHEMA_NAME}]},
        {"name": "date", "restrictions": [{"schema_name": SCHEMA_NAME}]},
        {"name": "degree", "restrictions": [{"schema_name": SCHEMA_NAME}]},
    ]
    req_preds = [
        {
            "name": "birthdate_dateint",
            "p_type": "<=",
            "p_value": int(birth_date.strftime(birth_date_format)),
            "restrictions": [{"schema_name": SCHEMA_NAME}],
        }
    ]
    
    proof_request_anoncreds = {
        "name": "Proof of Education",
        "version": "1.0",
        "requested_attributes": {
            f"0_{req_attr['name']}_uuid": req_attr for req_attr in req_attrs
        },
        "requested_predicates": {
            f"0_{req_pred['name']}_GE_uuid": req_pred for req_pred in req_preds
        },
    }
    
    presentation_request = {"anoncreds": proof_request_anoncreds}
    proof_request_web_request = {
        "presentation_request": presentation_request,
        "trace": exchange_tracing,
    }
    if not connectionless:
        proof_request_web_request["connection_id"] = connection_id

    return proof_request_web_request

# --- Função Principal (main) ---

async def main():
    async with aiohttp.ClientSession() as session:
        # 1. Espera os agentes
        await asyncio.gather(
            wait_for_agent(session, ISSUER_ADMIN, "Issuer"),
            wait_for_agent(session, HOLDER_ADMIN, "Holder"),
            wait_for_agent(session, VERIFIER_ADMIN, "Verifier")
        )
        log_status("--- Todos os agentes estão online! ---")

        # 2. Setup do Issuer: DID Público, Schema e CredDef
        public_did = await get_public_did(session)
        if not public_did:
            return
        
        cred_def_id = await create_schema_and_cred_def(session, public_did)
        if not cred_def_id:
            return
            
        log_status(f"--- Issuer pronto para emitir (CredDef: {cred_def_id}) ---")

        # 3. Conectar Issuer e Holder
        connection_id, _ = await create_connection(session)
        if not connection_id:
            return
            
        log_status(f"--- Conexão estabelecida (ID: {connection_id}) ---")

        # 4. Iniciar o Loop Interativo
        exchange_tracing = False
        
        # Menu simplificado (removendo revogação, multitenancy, etc.)
        options = (
            "    (1) Issue Credential\n"
            "    (2) Send Proof Request\n"
            "    (2a) Send *Connectionless* Proof Request\n"
            "    (3) Send Message\n"
            "    (4) Create New Invitation\n"
            "    (T) Toggle tracing on credential/proof exchange\n"
            "    (X) Exit?\n[1/2/2a/3/4/T/X] "
        )

        async for option in prompt_loop(options):
            if option is None or option in "xX":
                log_msg("Saindo...")
                break

            elif option in "tT":
                exchange_tracing = not exchange_tracing
                log_msg(
                    f">>> Credential/Proof Exchange Tracing is {'ON' if exchange_tracing else 'OFF'}"
                )

            elif option == "1":
                log_status("# Emitindo Credencial de Diploma para o Holder...")
                offer_request = generate_credential_offer(
                    connection_id, cred_def_id, exchange_tracing
                )
                await session.post(
                    f"{ISSUER_ADMIN}/issue-credential-2.0/send-offer", json=offer_request
                )

            elif option == "2":
                log_status("# Solicitando Prova de Diploma do Holder...")
                proof_request = generate_proof_request(
                    connection_id, exchange_tracing
                )
                await session.post(
                    f"{ISSUER_ADMIN}/present-proof-2.0/send-request", json=proof_request
                )

            elif option == "2a":
                log_status("# Criando Pedido de Prova *Sem Conexão*...")
                proof_request_payload = generate_proof_request(
                    connection_id, exchange_tracing, connectionless=True
                )
                
                # Criar o pedido de prova
                async with session.post(
                    f"{ISSUER_ADMIN}/present-proof-2.0/create-request", 
                    json=proof_request_payload
                ) as resp:
                    if resp.status != 200:
                        log_msg(f"Erro ao criar pedido de prova: {await resp.text()}")
                        continue
                    proof_request_data = await resp.json()
                
                # Gerar URL e QR Code (adaptado do faber.py)
                pres_req_id = proof_request_data["pres_ex_id"]
                # Assumindo que o Issuer está acessível em localhost:8000
                url = f"http://localhost:8000/webhooks/pres_req/{pres_req_id}/"
                
                log_msg(f"URL do Pedido de Prova: {url}")
                qr = QRCode(border=1)
                qr.add_data(url)
                log_msg("Escaneie o QR code com um agente móvel:")
                qr.print_ascii(invert=True)

            elif option == "3":
                msg = await prompt("Enter message: ")
                await session.post(
                    f"{ISSUER_ADMIN}/connections/{connection_id}/send-message",
                    {"content": msg},
                )

            elif option == "4":
                log_status("Criando novo convite...")
                # Esta conexão não será usada pelo loop,
                # mas permite que outro agente se conecte.
                await create_connection(session)

        log_status("--- Fim do controlador interativo ---")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log_msg("\nParando...")
        os._exit(1)