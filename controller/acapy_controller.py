import aiohttp
import logging
from typing import Dict, Any

#  URLs dos Agentes (Constantes) 
ISSUER_ADMIN = "http://localhost:8001"
HOLDER_ADMIN = "http://localhost:8011"
VERIFIER_ADMIN = "http://localhost:8021"

# Estado do Sistema (Simples) 
# Em um sistema real, isso seria um banco de dados.
# Vamos armazenar os IDs que geramos aqui.
STATE = {
    "issuer_did": None,
    "selo_schema_id": None,
    "selo_cred_def_id": None,
    "produto_schema_id": None,
    "produto_cred_def_id": None,
    "conn_id_issuer_holder": None,
    "conn_id_verifier_holder": None,
}

#  Funções Auxiliares de API 
async def admin_request(session, method, url, json_data=None, params=None):
    """Função auxiliar para fazer chamadas de API genéricas."""
    try:
        async with session.request(method, url, json=json_data, params=params) as resp:
            resp.raise_for_status()
            return await resp.json()
    except aiohttp.ClientError as e:
        logging.error(f"Erro na API {method} {url}: {e}")
        return None

# --- Ferramentas do Chatbot ---

async def setup_marketplace(session: aiohttp.ClientSession) -> str:
    """Ferramenta 1: Configura o Issuer com os schemas e cred defs do marketplace."""
    logging.info("Iniciando setup do marketplace...")
    
    # 1. Obter DID
    did_info = await admin_request(session, "GET", f"{ISSUER_ADMIN}/wallet/did/public")
    if not did_info or not did_info.get("result", {}).get("did"):
        return "Erro: Não foi possível obter o DID público do Issuer."
    issuer_did = did_info["result"]["did"]
    STATE["issuer_did"] = issuer_did
    logging.info(f"Issuer DID: {issuer_did}")

    # 2. Criar Schema do Selo
    schema_selo_body = {
        "schema": {"issuerId": issuer_did, "name": "selo-vendedor", "version": "1.0", "attrNames": ["nome_vendedor", "nivel"]}
    }
    selo_schema_resp = await admin_request(session, "POST", f"{ISSUER_ADMIN}/anoncreds/schema", schema_selo_body)
    if not selo_schema_resp: return "Erro ao criar schema do selo."
    STATE["selo_schema_id"] = selo_schema_resp.get("schema_state", {}).get("schema_id")
    logging.info(f"Selo Schema ID: {STATE['selo_schema_id']}")

    # 3. Criar CredDef do Selo
    cred_def_selo_body = {
        "credential_definition": {"issuerId": issuer_did, "schemaId": STATE["selo_schema_id"], "tag": "selo"}
    }
    selo_cred_def_resp = await admin_request(session, "POST", f"{ISSUER_ADMIN}/anoncreds/credential-definition", cred_def_selo_body)
    if not selo_cred_def_resp: return "Erro ao criar cred def do selo."
    STATE["selo_cred_def_id"] = selo_cred_def_resp.get("credential_definition_state", {}).get("credential_definition_id")
    logging.info(f"Selo CredDef ID: {STATE['selo_cred_def_id']}")

    # 4. Criar Schema do Produto
    schema_prod_body = {
        "schema": {"issuerId": issuer_did, "name": "anuncio-produto", "version": "1.0", "attrNames": ["produto", "preco", "id_anuncio"]}
    }
    prod_schema_resp = await admin_request(session, "POST", f"{ISSUER_ADMIN}/anoncreds/schema", schema_prod_body)
    if not prod_schema_resp: return "Erro ao criar schema do produto."
    STATE["produto_schema_id"] = prod_schema_resp.get("schema_state", {}).get("schema_id")
    logging.info(f"Produto Schema ID: {STATE['produto_schema_id']}")

    # 5. Criar CredDef do Produto
    cred_def_prod_body = {
        "credential_definition": {"issuerId": issuer_did, "schemaId": STATE["produto_schema_id"], "tag": "produto"}
    }
    prod_cred_def_resp = await admin_request(session, "POST", f"{ISSUER_ADMIN}/anoncreds/credential-definition", cred_def_prod_body)
    if not prod_cred_def_resp: return "Erro ao criar cred def do produto."
    STATE["produto_cred_def_id"] = prod_cred_def_resp.get("credential_definition_state", {}).get("credential_definition_id")
    logging.info(f"Produto CredDef ID: {STATE['produto_cred_def_id']}")
    
    return "Marketplace configurado com sucesso! Schemas e CredDefs criados."

async def conectar_admin_vendedor(session: aiohttp.ClientSession) -> str:
    """Ferramenta 2: Conecta o Admin (Issuer) ao Vendedor (Holder)."""
    logging.info("Conectando Admin ao Vendedor...")
    
    # 1. Issuer cria convite
    invite_body = {"handshake_protocols": ["https://didcomm.org/didexchange/1.0"]}
    invite_resp = await admin_request(session, "POST", f"{ISSUER_ADMIN}/out-of-band/create-invitation", invite_body)
    if not invite_resp: return "Erro ao criar convite."
    invitation = invite_resp["invitation"]

    # 2. Holder recebe convite
    conn_resp = await admin_request(session, "POST", f"{HOLDER_ADMIN}/out-of-band/receive-invitation", invitation)
    if not conn_resp: return "Erro ao receber convite."
    
    # 3. Armazena o Conn ID (do lado do Issuer)
    # Em um app real, esperaríamos o 'state' ficar 'active' via webhook
    # Aqui, vamos apenas buscar o ID
    conn_list = await admin_request(session, "GET", f"{ISSUER_ADMIN}/connections", params={"their_label": "Holder"})
    if not conn_list or not conn_list.get("results"):
        return "Conexão iniciada, mas não foi possível encontrar o ID no Issuer."
    
    STATE["conn_id_issuer_holder"] = conn_list["results"][0]["connection_id"]
    logging.info(f"Conn ID (Issuer-Holder): {STATE['conn_id_issuer_holder']}")
    
    return "Conexão entre Admin e Vendedor estabelecida."

async def emitir_selo_vendedor(session: aiohttp.ClientSession, nome_vendedor: str, nivel: str) -> str:
    """Ferramenta 3: Emite um Selo de Vendedor para o Holder."""
    logging.info(f"Emitindo selo para {nome_vendedor}...")
    
    conn_id = STATE.get("conn_id_issuer_holder")
    cred_def_id = STATE.get("selo_cred_def_id")
    
    if not conn_id or not cred_def_id:
        return "Erro: Conecte o Admin ao Vendedor e configure o marketplace primeiro."

    issue_body = {
        "connection_id": conn_id,
        "filter": {"anoncreds": {"cred_def_id": cred_def_id}},
        "credential_preview": {
            "@type": "issue-credential/2.0/credential-preview",
            "attributes": [
                {"name": "nome_vendedor", "value": nome_vendedor},
                {"name": "nivel", "value": nivel}
            ]
        }
    }
    
    issue_resp = await admin_request(session, "POST", f"{ISSUER_ADMIN}/issue-credential-2.0/send", issue_body)
    if not issue_resp: return f"Erro ao emitir selo."
    
    return f"Selo de Vendedor '{nivel}' emitido para '{nome_vendedor}'."

# Você pode adicionar mais funções aqui, como `emitir_anuncio_produto`, etc.