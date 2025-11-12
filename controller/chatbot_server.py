import logging
import aiohttp
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from contextlib import asynccontextmanager

# Importa nossas funções
import acapy_controller
import ollama_client

# Configura o logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# --- Gerenciamento da Sessão HTTP ---
# Cria uma sessão aiohttp que dura por toda a vida da aplicação
# para reutilizar conexões com o ACA-Py.
app_state = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Inicia a sessão
    app_state["http_session"] = aiohttp.ClientSession()
    logging.info("Sessão aiohttp iniciada.")
    yield
    # Fecha a sessão
    await app_state["http_session"].close()
    logging.info("Sessão aiohttp fechada.")

app = FastAPI(lifespan=lifespan)

# Define o modelo de dados para a requisição de chat
class ChatMessage(BaseModel):
    message: str

#  Funções 
@app.post("/chat")
async def chat_endpoint(chat_message: ChatMessage):
    
    # 1. Obter a chamada de função do Ollama
    try:
        command = ollama_client.get_ollama_function_call(chat_message.message)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro no cliente Ollama: {e}")

    function_name = command.get("function_name")
    parameters = command.get("parameters", {})
    
    if function_name == "error":
        raise HTTPException(status_code=500, detail=f"Erro do Ollama: {parameters.get('message')}")
        
    # 2. Obter a sessão aiohttp
    session = app_state["http_session"]

    # 3. Executar a função correspondente
    result_message = ""
    try:
        if function_name == "setup_marketplace":
            result_message = await acapy_controller.setup_marketplace(session)
            
        elif function_name == "conectar_admin_vendedor":
            result_message = await acapy_controller.conectar_admin_vendedor(session)
            
        elif function_name == "emitir_selo_vendedor":
            # **parameters é um "unpacking" de dicionário
            # envia {"nome_vendedor": "...", "nivel": "..."} como argumentos
            result_message = await acapy_controller.emitir_selo_vendedor(session, **parameters)
            
        # (Adicione 'elif' para novas funções aqui)
            
        else:
            result_message = f"Erro: O LLM tentou chamar uma função desconhecida: {function_name}"
            
    except Exception as e:
        # Pega erros da lógica do controlador (ex: parâmetros faltando)
        raise HTTPException(status_code=400, detail=f"Erro ao executar '{function_name}': {e}")

    # 4. Retornar o resultado
    return {"response": result_message}

if __name__ == "__main__":
    import uvicorn
    # Inicia o servidor na porta 8080
    uvicorn.run(app, host="0.0.0.0", port=8080)