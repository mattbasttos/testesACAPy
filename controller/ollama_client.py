import requests
import json
import logging
from typing import Dict, Any  

OLLAMA_URL = "http://localhost:11434/api/generate"
# Mude de "llama3" para:
MODEL_NAME = "phi3:mini"

# O "MENU" DE FERRAMENTAS QUE O LLM PODE ESCOLHER
SYSTEM_PROMPT = """
Você é um assistente de chatbot para um marketplace de identidade descentralizada.
Sua tarefa é traduzir a linguagem natural do usuário em uma chamada de função JSON.
Responda APENAS com o objeto JSON e nada mais. Não adicione explicações.

O JSON deve ter o formato:
{"function_name": "nome_da_funcao", "parameters": {"arg1": "valor1", ...}}

As funções disponíveis são:

1. setup_marketplace
   - Descrição: Configura a plataforma (cria todos os Schemas e CredDefs).
   - Parâmetros: {}
   - Exemplo de Uso: "Configure a plataforma", "Prepare o marketplace"

2. conectar_admin_vendedor
   - Descrição: Cria uma conexão entre o Admin (Issuer) e o Vendedor (Holder).
   - Parâmetros: {}
   - Exemplo de Uso: "Registre um novo vendedor", "Conecte o admin ao vendedor"

3. emitir_selo_vendedor
   - Descrição: Emite um "Selo de Vendedor Verificado" para o vendedor.
   - Parâmetros:
     - "nome_vendedor": (string) O nome ou ID do vendedor.
     - "nivel": (string) O nível de verificação (ex: Ouro, Prata, Bronze).
   - Exemplo de Uso: "Emita um selo Ouro para o Vendedor_123", "Verificar Vendedor_ABC como Prata"

(Você pode adicionar mais funções aqui, como 'emitir_anuncio' ou 'solicitar_prova')

Traduza o prompt do usuário para UMA ÚNICA chamada de função JSON.
"""

def get_ollama_function_call(user_prompt: str) -> Dict[str, Any]:
    """
    Envia o prompt do usuário para o Ollama e retorna a chamada de função JSON.
    """
    logging.info(f"Ollama recebendo: {user_prompt}")
    
    # Formata o prompt completo (System Prompt + User Prompt)
    full_prompt = f"{SYSTEM_PROMPT}\nPROMPT DO USUÁRIO: \"{user_prompt}\""
    
    payload = {
        "model": MODEL_NAME,
        "prompt": full_prompt,
        "stream": False,
        "format": "json"  # Pede ao Ollama para garantir que a saída seja JSON
    }
    
    try:
        response = requests.post(OLLAMA_URL, json=payload)
        response.raise_for_status()
        
        # A resposta do Ollama está em 'response' (que é uma string JSON)
        response_json_str = response.json()["response"]
        
        # Analisa a string JSON interna para obter o objeto
        function_call_json = json.loads(response_json_str)
        
        logging.info(f"Ollama retornou: {function_call_json}")
        return function_call_json
        
    except requests.exceptions.RequestException as e:
        logging.error(f"Erro ao chamar Ollama: {e}")
        return {"function_name": "error", "parameters": {"message": str(e)}}
    except json.JSONDecodeError as e:
        logging.error(f"Erro ao analisar JSON do Ollama: {e}")
        logging.error(f"String recebida: {response_json_str}")
        return {"function_name": "error", "parameters": {"message": "Ollama retornou JSON inválido"}}