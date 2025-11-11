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



O comando `pull` baixa um novo modelo (como o `llama3` ou `phi3:mini`) do registro do Ollama para o seu computador.



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



## 4\. Fluxo de Trabalho Padrão (Resumo)



Para o nosso projeto de chatbot, seu fluxo de trabalho será:



1.  **Verificar se o Ollama está rodando:**



    ```bash

    sudo systemctl status ollama

    ```



    (Se não estiver, use `sudo systemctl start ollama`.)



2.  **Baixar o modelo (apenas uma vez):**



    ```bash

    ollama pull phi3:mini

    ```



3.  **Iniciar seu aplicativo:**



    ```bash

    (venv) python chatbot_server.py

    ```



4.  **Testar com `curl`:**



    ```bash

    curl -X POST http://localhost:8080/chat -d '{"message": "Prepare o marketplace"}'

    ```



5.  **Se algo falhar (Erro 500):**



    ```bash

    sudo systemctl restart ollama

    ```