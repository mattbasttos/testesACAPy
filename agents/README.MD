# Tutorial: Simulando um Marketplace com ACA-Py e Swagger

Este tutorial guia você pela simulação de um marketplace seguro usando três agentes ACA-Py, controlados diretamente pela interface Swagger (OpenAPI).

### Cenário

  * **Issuer (Admin):** O Administrador do Marketplace (`http://localhost:8001/api/doc`).
      * *Função:* Emite um "Selo de Vendedor Verificado" e um "Anúncio de Produto".
  * **Holder (Vendedor):** O Vendedor (`http://localhost:8011/api/doc`).
      * *Função:* Recebe o selo e o anúncio.
  * **Verifier (Comprador):** O Comprador (`http://localhost:8021/api/doc`).
      * *Função:* Verifica o selo e o anúncio do vendedor antes de comprar.

### Pré-requisitos

1.  **Terminais Ativos:**
      * `von-network` (ou outra rede ledger)
      * `issuer/run-issuer.py`
      * `holder/run-holder.py`
      * `verifier/run-verifier.py`
2.  **Abas do Navegador Abertas:**
      * **Issuer:** `http://localhost:8001/api/doc`
      * **Holder:** `http://localhost:8011/api/doc`
      * **Verifier:** `http://localhost:8021/api/doc`

### Preparação: Limpar Wallets Antigas

Para evitar erros de "Schema already exists", é recomendado limpar as wallets antes de começar. Pare os agentes, execute os comandos abaixo e reinicie os agentes.

```bash
rm -rf ~/.indy_client/wallet/issuer_wallet_prod
rm -rf ~/.indy_client/wallet/holder_wallet_clean
rm -rf ~/.indy_client/wallet/verifier_wallet_clean
```

-----

### Fase 0: Setup dos Schemas (O Admin prepara a plataforma)

O Issuer (Admin) define as credenciais que a plataforma usará.

#### 0.1. Obter o DID Público do Issuer (Admin)

  * **Onde:** Aba do **Issuer (Admin)** (`8001`)
  * **Endpoint:** `GET /wallet/did/public`
  * **Ação:** "Try it out" -\> "Execute".
  * **Resultado:** Copie o valor do `did` de `result`.
  * **Salve como:** `[SEU_ISSUER_ID]`

#### 0.2. Criar Schema 1: "Selo de Vendedor Verificado"

  * **Onde:** Aba do **Issuer (Admin)**
  * **Endpoint:** `POST /anoncreds/schema`
  * **Ação:** "Try it out" e cole este JSON (substitua o `issuerId`):
    ```json
    {
      "schema": {
        "issuerId": "[SEU_ISSUER_ID]",
        "name": "selo-vendedor",
        "version": "1.0",
        "attrNames": ["nome_vendedor", "nivel", "data_verificacao"]
      }
    }
    ```
  * **Resultado:** Copie o `schema_id` de `schema_state`.
  * **Salve como:** `[SELO_SCHEMA_ID]`

#### 0.3. Criar CredDef 1 (para o "Selo")

  * **Onde:** Aba do **Issuer (Admin)**
  * **Endpoint:** `POST /anoncreds/credential-definition`
  * **Ação:** "Try it out" e cole este JSON (substitua os IDs):
    ```json
    {
      "credential_definition": {
        "issuerId": "[SEU_ISSUER_ID]",
        "schemaId": "[SELO_SCHEMA_ID]",
        "tag": "selo",
        "support_revocation": false
      }
    }
    ```
  * **Resultado:** Copie o `credential_definition_id` de `credential_definition_state`.
  * **Salve como:** `[SELO_CRED_DEF_ID]`

#### 0.4. Criar Schema 2: "Anúncio de Produto"

  * **Onde:** Aba do **Issuer (Admin)**
  * **Endpoint:** `POST /anoncreds/schema`
  * **Ação:** "Try it out" e cole este JSON:
    ```json
    {
      "schema": {
        "issuerId": "[SEU_ISSUER_ID]",
        "name": "anuncio-produto",
        "version": "1.0",
        "attrNames": ["produto", "preco", "condicao", "id_anuncio"]
      }
    }
    ```
  * **Resultado:** Copie o `schema_id` de `schema_state`.
  * **Salve como:** `[PRODUTO_SCHEMA_ID]`

#### 0.5. Criar CredDef 2 (para o "Anúncio")

  * **Onde:** Aba do **Issuer (Admin)**
  * **Endpoint:** `POST /anoncreds/credential-definition`
  * **Ação:** "Try it out" e cole este JSON:
    ```json
    {
      "credential_definition": {
        "issuerId": "[SEU_ISSUER_ID]",
        "schemaId": "[PRODUTO_SCHEMA_ID]",
        "tag": "produto",
        "support_revocation": false
      }
    }
    ```
  * **Resultado:** Copie o `credential_definition_id` de `credential_definition_state`.
  * **Salve como:** `[PRODUTO_CRED_DEF_ID]`

-----

### Fase 1: Conexão (Admin e Vendedor)

#### 1.1. Issuer (Admin) Cria o Convite OOB

  * **Onde:** Aba do **Issuer (Admin)** (`8001`)
  * **Endpoint:** `POST /out-of-band/create-invitation`
  * **Ação:**
    1.  Clique em **"Try it out"**.
    2.  No campo `create_request_body`, cole este JSON:
        ```json
        {
          "handshake_protocols": [
            "https://didcomm.org/didexchange/1.0"
          ]
        }
        ```
    3.  Clique em **"Execute"**.
  * **Resultado:** Copie **apenas o objeto `invitation`** de dentro da resposta.

#### 1.2. Holder (Vendedor) Recebe o Convite

  * **Onde:** Aba do **Holder (Vendedor)** (`8011`)
  * **Endpoint:** `POST /out-of-band/receive-invitation`
  * **Ação:**
    1.  Clique em **"Try it out"**.
    2.  **Cole o objeto `invitation`** do passo anterior no campo "Request body".
    3.  Clique em **"Execute"**.

#### 1.3. Issuer (Admin) Encontra o ID da Conexão Correta

O `connection_id` não é universal. Você deve obter o ID no lado do Issuer.

  * **Onde:** Aba do **Issuer (Admin)** (`8001`)
  * **Endpoint:** `GET /connections`
  * **Ação:**
    1.  Clique em **"Try it out"**.
    2.  No campo `their_label`, digite `Holder` (o label do seu script `run_holder.py`).
    3.  Clique em **"Execute"**.
  * **Resultado:** Você verá a conexão com o Holder. Copie o `connection_id` deste registro.
  * **Salve como:** `[CONN_ID_ISSUER_HOLDER]`

-----

### Fase 2: Emissão (O Vendedor ganha o Selo e o Anúncio)

#### 2.1. Emitir o "Selo de Vendedor Verificado"

  * **Onde:** Aba do **Issuer (Admin)** (`8001`)
  * **Endpoint:** `POST /issue-credential-2.0/send`
  * **Ação:** "Try it out" e cole este JSON (use os IDs corretos):
    ```json
    {
      "connection_id": "[CONN_ID_ISSUER_HOLDER]",
      "comment": "Emitindo Selo de Vendedor Ouro",
      "filter": {
        "anoncreds": {
          "cred_def_id": "[SELO_CRED_DEF_ID]"
        }
      },
      "credential_preview": {
        "@type": "issue-credential/2.0/credential-preview",
        "attributes": [
          {"name": "nome_vendedor", "value": "Vendedor_123"},
          {"name": "nivel", "value": "Ouro"},
          {"name": "data_verificacao", "value": "2025-11-05"}
        ]
      }
    }
    ```
  * **Ação:** Clique em **"Execute"**.

#### 2.2. Emitir o "Anúncio de Produto"

  * **Onde:** Aba do **Issuer (Admin)** (`8001`)
  * **Endpoint:** `POST /issue-credential-2.0/send`
  * **Ação:** "Try it out" e cole este JSON (use o `cred_def_id` do produto):
    ```json
    {
      "connection_id": "[CONN_ID_ISSUER_HOLDER]",
      "comment": "Anunciando Placa de Vídeo",
      "filter": {
        "anoncreds": {
          "cred_def_id": "[PRODUTO_CRED_DEF_ID]"
        }
      },
      "credential_preview": {
        "@type": "issue-credential/2.0/credential-preview",
        "attributes": [
          {"name": "produto", "value": "Placa de Vídeo RTX 4090"},
          {"name": "preco", "value": "10000.00"},
          {"name": "condicao", "value": "Nova"},
          {"name": "id_anuncio", "value": "AD-98765"}
        ]
      }
    }
    ```
  * **Ação:** Clique em **"Execute"**.

#### 2.3. Vendedor (Holder) Verifica sua Carteira

  * **Onde:** Aba do **Holder (Vendedor)** (`8011`)
  * **Endpoint:** `GET /credentials`
  * **Ação:** "Try it out" -\> "Execute".
  * **Resultado:** Inspecione a lista `results`. Ela agora conterá as **duas credenciais** (o Selo e o Anúncio).

-----

### Fase 3: Verificação (Comprador e Vendedor)

#### 3.1. Conectar Comprador e Vendedor

1.  **Verifier (Comprador) Cria Convite:**

      * **Onde:** Aba do **Verifier (Comprador)** (`8021`)
      * **Endpoint:** `POST /out-of-band/create-invitation`
      * **Ação:** "Try it out", cole o JSON `{"handshake_protocols": ["https://didcomm.org/didexchange/1.0"]}` -\> "Execute".
      * **Resultado:** **Copie o objeto `invitation`**.

2.  **Holder (Vendedor) Recebe Convite:**

      * **Onde:** Aba do **Holder (Vendedor)** (`8011`)
      * **Endpoint:** `POST /out-of-band/receive-invitation`
      * **Ação:** "Try it out", cole o convite do **Comprador** -\> "Execute".

3.  **Verifier (Comprador) Encontra o ID da Conexão Correta:**

      * **Onde:** Aba do **Verifier (Comprador)** (`8021`)
      * **Endpoint:** `GET /connections`
      * **Ação:** "Try it out", `their_label`: `Holder` -\> "Execute".
      * **Resultado:** Copie o `connection_id` deste registro.
      * **Salve como:** `[CONN_ID_VERIFIER_HOLDER]`

#### 3.2. Comprador (Verifier) Solicita a Prova Combinada

  * **Onde:** Aba do **Verifier (Comprador)** (`8021`)
  * **Endpoint:** `POST /present-proof-2.0/send-request`
  * **Ação:** "Try it out" e cole este JSON (substitua os IDs):
    ```json
    {
      "connection_id": "[CONN_ID_VERIFIER_HOLDER]",
      "comment": "Quero comprar sua RTX 4090. Prove que você é verificado e que tem o anúncio.",
      "presentation_request": {
        "anoncreds": {
          "name": "Prova de Compra Segura",
          "version": "1.0",
          "requested_attributes": {
            "ref1_nome_vendedor": {
              "name": "nome_vendedor",
              "restrictions": [
                {
                  "cred_def_id": "[SELO_CRED_DEF_ID]"
                }
              ]
            },
            "ref2_produto": {
              "name": "produto",
              "restrictions": [
                {
                  "cred_def_id": "[PRODUTO_CRED_DEF_ID]"
                }
              ]
            },
            "ref3_preco": {
              "name": "preco",
              "restrictions": [
                {
                  "cred_def_id": "[PRODUTO_CRED_DEF_ID]"
                }
              ]
            }
          },
          "requested_predicates": {}
        }
      }
    }
    ```
  * **Ação:** Clique em **"Execute"**.

#### 3.3. Comprador (Verifier) Verifica a Prova

O Holder (Vendedor) irá responder automaticamente (graças às suas flags `--auto-respond...`).

  * **Onde:** Aba do **Verifier (Comprador)** (`8021`)
  * **Endpoint:** `GET /present-proof-2.0/records`
  * **Ação:** "Try it out" -\> "Execute".
  * **Resultado:** Encontre o registro de prova na lista `results`. O estado (`state`) deve ser `verified` e o campo `verified` deve ser `true`.

-----

### Conclusão do Fluxo

Você executou manualmente todo o ciclo de SSI para um cenário de marketplace:

1.  O **Admin** criou as definições da plataforma (Schemas/CredDefs).
2.  O **Vendedor** se conectou ao Admin e recebeu duas credenciais (Selo e Anúncio).
3.  O **Comprador** se conectou ao Vendedor e solicitou uma prova combinada de ambas as credenciais.
4.  O **Comprador** verificou criptograficamente a prova, estabelecendo confiança para a transação.
