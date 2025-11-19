# Guia Rápido: Comandos Essenciais do Ollama



Este guia cobre os comandos básicos para gerenciar o Ollama em um ambiente Linux, com foco em como o usamos para o projeto do chatbot ACA-Py.



## 1\. Gerenciando o Serviço (Comandos `systemctl`)



Na maioria das instalações do Linux, o Ollama roda como um **serviço de segundo plano** (`systemd`). Você não o inicia manualmente com `ollama serve`; você gerencia o serviço.



### verificar o status



Este é o comando mais importante. Ele mostra se o Ollama está rodando, se falhou, ou se está parado.



```bash

sudo systemctl status ollama

```



  * **Se você vir `active (running)`:** O servidor está no ar e pronto.

  * **Se você vir `inactive (dead)`:** O servidor está parado.



### Iniciar o serviço



Use este comando se o status mostrar `inactive (dead)` e você quiser ligá-lo.



```bash

sudo systemctl start ollama

```



### Parar o serviço



Use este comando para forçar a parada do servidor.



```bash

sudo systemctl stop ollama

```



### Reiniciar o serviço (O Mais Útil para Erros 500)



Se você receber um `Erro 500` do Ollama, significa que o servidor travou. Reiniciá-lo é a melhor solução.



```bash

sudo systemctl restart ollama

```



-----



## 2\. Baixando Novos Modelos (LLMs)



O comando `pull` baixa um novo modelo (como o `llama3` ou `phi3:mini`) do registro do Ollama para o seu computador. Neste projeto foi utilizado o Phi3:mini.



```bash

ollama pull <nome-do-modelo>

```



**Exemplos que usamos:**



  * Para baixar o Llama 3 (grande, poderoso):

    ```bash

    ollama pull llama3

    ```

  * Para baixar o Phi-3 Mini (pequeno, rápido, ótimo para testes):

    ```bash

    ollama pull phi3:mini

    ```



-----



## 3\. O Comando `ollama serve` (O que NÃO fazer)



Este comando tenta iniciar *manualmente* um novo servidor Ollama no seu terminal.



```bash

ollama serve

```



Quase sempre, você **não deve** usar este comando, porque o serviço (`systemctl`) **já está rodando em segundo plano**.



Se você tentar usá-lo, verá este erro, que é na verdade uma **boa notícia**:



```bash

Error: listen tcp 127.0.0.1:11434: bind: address already in use

```



Isso simplesmente confirma que o servidor principal já está no ar e ocupando a porta `11434`. Apenas feche este terminal e continue.



-----



# 4\. Roteiro de Execução (Passo a Passo)

Para que o sistema funcione, os componentes devem ser iniciados nesta ordem exata. Use terminais separados para cada um.

### Passo A: Infraestrutura SSI

1.  **Terminal 1 (Ledger):** Inicie a VON Network.
2.  **Terminal 2 (Issuer):** `python issuer/run_issuer.py`
3.  **Terminal 3 (Holder):** `python holder/run_holder.py`
4.  *(Opcional)* **Terminal 4 (Verifier):** `python verifier/run_verifier.py`

### Passo B: Servidor do Chatbot

Vá para a pasta do controlador e inicie a API.

**Terminal 5:**

```bash
cd ~/testesACAPy/controller
source ../venv/bin/activate
python chatbot_server.py
```

  * **Sucesso:** Você verá `Uvicorn running on http://0.0.0.0:8080`.

-----

## 5\. Comandos de Teste (Demo Script)

Use um **Terminal 6** para enviar os comandos de voz (simulados via texto) para o seu bot.

### 1️⃣ Configurar o Ambiente

O bot deve criar Schemas e CredDefs no Issuer.

```bash
curl -X POST http://localhost:8080/chat \
     -H "Content-Type: application/json" \
     -d '{"message": "Prepare o marketplace para mim"}'
```

### 2️⃣ Conectar Agentes

O bot deve criar um convite OOB no Issuer e fazê-lo ser aceito pelo Holder.

```bash
curl -X POST http://localhost:8080/chat \
     -H "Content-Type: application/json" \
     -d '{"message": "Conecte o administrador com o vendedor"}'
```

### 3️⃣ Emitir Credencial (O Grande Teste)

O bot deve entender os parâmetros "Nome" e "Nível" da frase e emitir a credencial.

```bash
curl -X POST http://localhost:8080/chat \
     -H "Content-Type: application/json" \
     -d '{"message": "Emita um selo nível Ouro para a loja TechStore"}'
```