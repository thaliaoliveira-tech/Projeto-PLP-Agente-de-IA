# Jython AI Agent

## Exemplos com Caelum Stella

```text
O CPF 529.982.247-25 é válido?              -> stella_validate_document
Formate o CPF 52998224725.                  -> stella_transform_document
Gere um CNPJ válido para teste.             -> stella_generate_document
Escreva 123 por extenso.                    -> stella_number_to_words
Quais documentos a Stella consegue gerar?   -> stella_capabilities
Valide estes CPFs em lote: 52998224725,...  -> stella_validate_batch
```

Para documentos reais, prefira o modo local `/stella`, que não envia o valor à
Groq. Veja a lista completa de parâmetros e exemplos em
[`knowledge/05_tools.md`](knowledge/05_tools.md).

> A integração Caelum Stella valida documentos brasileiros localmente. Use
> `/stella` para não enviar documentos à Groq; veja `knowledge/09_stella.md`.

> Assistente técnico **agentivo** de terminal, escrito em **Python**, executado
> pelo **Jython** sobre a **JVM**. Conversa com o modelo `openai/gpt-oss-120b`
> na **Groq** e executa ferramentas locais — consultar a documentação do
> projeto, rodar a suíte de testes, pesquisar conversas antigas e apurar
> métricas de uso — sempre através de **APIs Java**.

```text
Python  ->  Jython  ->  JVM  ->  Classes Java  ->  Groq API  ->  Tools locais
```

**Disciplina:** Paradigmas de Linguagens de Programação — 2026.2
**Atividade:** Usar o compilador Jython

```text
==================================================
              JYTHON AI AGENT
==================================================

Jython : 2.7.4
Java   : 11.0.32
Modelo : openai/gpt-oss-120b
Tools  : 6
Banco  : conectado (sessão 3)
KB     : 8 documentos (25 trechos)

Você: rode os testes de fuzzy

[executando os testes... 495 ms]

Assistente:
Foram executados os testes de fuzzy. Todos os 4 testes passaram:

- T08 – Busca fuzzy com correspondência exata
- T09 – Busca fuzzy com erro de digitação
- T10 – Knowledge Search respeita top_k
- T14 – Busca fuzzy no histórico de conversas

Tempo total: 422 ms. Nenhum erro foi encontrado.

   [1.9s | 2 chamada(s) LLM | tools: run_project_tests | 1402 tokens]
```

---

## Sobre o projeto

O **Jython AI Agent** não é um chatbot que apenas repassa perguntas para uma
API. O modelo é um **orquestrador**: ele decide, a cada pergunta, se consegue
responder sozinho ou se precisa executar uma das seis ferramentas locais do
projeto. A aplicação executa a ferramenta, devolve o resultado ao modelo, e
só então a resposta em linguagem natural chega ao terminal.

O ponto central continua sendo **como** isso foi construído: todo o código é
Python, mas nenhuma biblioteca Python esconde a plataforma Java. Rede, streams,
coleções, banco de dados, normalização Unicode e similaridade textual são
resolvidos com classes e bibliotecas Java chamadas diretamente do código
Python.

Deliberadamente **não** são usados:

```text
requests    urllib    httplib    sqlite3    groq-python    openai-python    Flask
```

Qualquer um deles esconderia exatamente a integração Java que este trabalho
precisa demonstrar.

---

## Objetivo acadêmico

A atividade pede programas em Python, executados pelo Jython, que façam uso
efetivo de classes e bibliotecas Java, deixando evidente a interoperabilidade
entre as duas linguagens.

Este projeto cobre **cinco** frentes de APIs Java de uma só vez:

| Necessidade do agente         | API Java usada                       |
| ----------------------------- | ------------------------------------ |
| Comunicação de rede           | `java.net`                           |
| Manipulação de streams        | `java.io`                            |
| Estruturas de dados           | `java.util`                          |
| Configuração e ambiente       | `java.lang`, `java.text`, `java.time` |
| Banco de dados                | `java.sql` (JDBC + SQLite)           |
| Biblioteca Java de terceiros  | Apache Commons Text                  |

E estrutura toda a aplicação no programa principal:

| Componente | O que demonstra |
| ---------- | --------------- |
| `main.py`  | O agente completo, combinando networking Java, I/O UTF-8, JDBC SQLite, Collections e busca fuzzy |
| `tests/`   | Suíte com 15 testes unitários validando cada integração com a JVM |

---

## O que é Jython

**Jython** é uma implementação da linguagem Python que executa sobre a **Java
Virtual Machine (JVM)**. Diferentemente do CPython (o interpretador Python
tradicional, escrito em C), o Jython compila o código Python para *bytecode*
Java e o executa na JVM.

A consequência prática é a que este projeto explora: **classes e bibliotecas
Java podem ser importadas e usadas diretamente dentro do código Python**, como
se fossem módulos Python.

|                               | CPython               | Jython                 |
| ----------------------------- | --------------------- | ---------------------- |
| Escrito em                    | C                     | Java                   |
| Executa sobre                 | Interpretador próprio | JVM                    |
| Compila para                  | bytecode CPython      | **bytecode Java**      |
| Usa bibliotecas Java          | Não                   | **Sim, nativamente**   |
| Usa extensões C (NumPy, etc.) | Sim                   | Não                    |
| Versão da linguagem           | 3.x                   | 2.7                    |

Neste projeto, a lógica do agente é escrita em Python, enquanto os recursos da
plataforma Java são usados para comunicação HTTP, manipulação de streams,
acesso a variáveis de ambiente, armazenamento do contexto, persistência em
banco e cálculo de similaridade textual.

---

## Arquitetura

```text
                        ┌─────────────────────┐
                        │       Usuário       │
                        │      (terminal)     │
                        └──────────┬──────────┘
                                   │ java.io.BufferedReader
                                   ▼
                        ┌─────────────────────┐
                        │  Agent Orchestrator │
                        │ openai/gpt-oss-120b │
                        │      via Groq       │
                        └──────────┬──────────┘
                                   │
                      decide se precisa de tool
                                   │
             ┌─────────────────────┼─────────────────────┐
             ▼                     ▼                     ▼
     Knowledge Tool          Testing Tool        Observability Tools
             │                     │                     │
       busca fuzzy             unittest           SQLite via JDBC
             │                     │                     │
       knowledge/*.md           tests/          histórico + métricas
             │                     │                     │
             └─────────────────────┼─────────────────────┘
                                   │
                                   ▼
                       resultado volta ao modelo
                                   │
                                   ▼
                     resposta em linguagem natural
```

Há **um único LLM orquestrador** e **seis ferramentas determinísticas**. Os
três "agentes lógicos" do desenho são áreas de responsabilidade, não instâncias
separadas de IA — o que reduz tokens, reduz latência e mantém o comportamento
testável.

---

## Como funciona

Fluxo completo de uma pergunta:

```text
 1. java.io.BufferedReader lê a linha digitada
 2. o orquestrador abre uma interação no SQLite
 3. a pergunta vira java.util.LinkedHashMap dentro do ArrayList do contexto
 4. groq_client monta o JSON: histórico + 6 tool schemas
 5. java.net.URL + HttpURLConnection abrem o POST HTTPS
 6. java.io.OutputStreamWriter escreve o JSON no socket
 7. a Groq responde: texto final OU tool_calls
 8. InputStreamReader + BufferedReader leem a resposta
 9. a chamada é gravada em llm_calls (tokens, cache, tempos)
10. havendo tool_calls: valida na lista branca, executa localmente,
    grava em tool_executions e devolve como mensagem role="tool"
11. volta ao passo 4 até vir texto (limite: AGENT_MAX_ITERATIONS)
12. java.io.PrintWriter imprime a resposta no terminal
```

Uma pergunta comum gasta **1 chamada** à LLM; uma que usa ferramenta gasta
**2** (a primeira devolve `tool_calls`, a segunda devolve o texto final).

O JSON enviado à Groq tem esta forma:

```json
{
  "model": "openai/gpt-oss-120b",
  "messages": [
    { "role": "system", "content": "Você é o assistente do Jython AI Agent..." },
    { "role": "user",   "content": "como o projeto conversa com a Groq?" }
  ],
  "tools": [ { "type": "function", "function": { "name": "search_project_knowledge" } } ],
  "tool_choice": "auto",
  "temperature": 0.4,
  "max_completion_tokens": 1500,
  "stream": false
}
```

E a resposta, quando o modelo quer uma ferramenta, vem assim:

```json
{
  "choices": [{
    "finish_reason": "tool_calls",
    "message": {
      "role": "assistant",
      "content": null,
      "tool_calls": [{
        "id": "call_abc123",
        "type": "function",
        "function": {
          "name": "search_project_knowledge",
          "arguments": "{\"query\": \"comunicação groq http\"}"
        }
      }]
    }
  }]
}
```

---

## Integração Python + Java

Este é o trecho mais importante do trabalho. Os arquivos do projeto começam
assim:

```python
from java.lang import System              # config.py, main.py
from java.net  import URL                 # groq_client.py
from java.net  import HttpURLConnection
from java.io   import OutputStreamWriter, InputStreamReader, BufferedReader
from java.io   import PrintWriter
from java.util import ArrayList, LinkedHashMap, Collections
from java.sql  import DriverManager       # database/connection.py
from java.text import Normalizer          # search/normalizer.py

from org.apache.commons.text.similarity import JaroWinklerSimilarity
```

Apesar de os arquivos terem extensão `.py` e sintaxe Python, **essas classes
pertencem à plataforma Java**. O Jython torna possível utilizá-las diretamente
porque o código Python é executado sobre a JVM: o `import` procura primeiro nos
módulos Python e, para pacotes Java, delega ao *classloader* da JVM.

### 1. Lendo o ambiente com Java

```python
from java.lang import System

GROQ_API_KEY = System.getenv("GROQ_API_KEY")
GROQ_MODEL   = System.getenv("GROQ_MODEL") or "openai/gpt-oss-120b"
```

Até a configuração do projeto passa por uma classe Java.

### 2. POST HTTPS com Java

```python
url = URL(self.api_url)                    # java.net.URL
connection = url.openConnection()          # java.net.HttpURLConnection

connection.setRequestMethod("POST")
connection.setRequestProperty("Content-Type", "application/json; charset=utf-8")
connection.setRequestProperty("Authorization", "Bearer " + self.api_key)
connection.setDoOutput(True)

writer = OutputStreamWriter(connection.getOutputStream(), "UTF-8")
writer.write(payload)                      # envia o JSON
writer.flush()
writer.close()

status = connection.getResponseCode()
reader = BufferedReader(InputStreamReader(connection.getInputStream(), "UTF-8"))
```

### 3. Coleção Java percorrida por um `for` de Python

```python
from java.util import ArrayList, LinkedHashMap

self.history = ArrayList()                 # o contexto NÃO é uma lista Python

message = LinkedHashMap()
message.put("role", "user")
message.put("content", texto)
self.history.add(message)

for message in self.history:               # for de Python sobre ArrayList Java
    payload.append({
        "role":    message.get("role"),
        "content": message.get("content"),
    })
```

### 4. Banco de dados com JDBC

```python
from java.sql import DriverManager

JavaClass.forName("org.sqlite.JDBC")
connection = DriverManager.getConnection("jdbc:sqlite:/app/data/jython_ai_chat.db")

statement = connection.prepareStatement(
    "INSERT INTO messages (role, content, created_at) VALUES (?, ?, ?)")
statement.setString(1, "user")
statement.setString(2, texto)
statement.executeUpdate()
```

Nenhuma linha usa o módulo `sqlite3` do CPython: é `java.sql` do começo ao fim.

### 5. Biblioteca Java de terceiros

```python
from org.apache.commons.text.similarity import JaroWinklerSimilarity
from org.apache.commons.text.similarity import LevenshteinDistance

_JARO_WINKLER = JaroWinklerSimilarity()
similaridade = float(_JARO_WINKLER.apply("docker", "doker"))   # 0.9556
```

Além das APIs padrão, o projeto usa uma **biblioteca Java externa**, resolvida
por Maven e colocada no classpath da JVM.

### 6. Remoção de acentos com `java.text`

```python
from java.text import Normalizer

decomposed = Normalizer.normalize("configuração", Normalizer.Form.NFD)
# -> "configurac~ao" -> remove as marcas combinantes -> "configuracao"
```

### 7. Exceções Java capturadas por `except` de Python

```python
from java.net import UnknownHostException, SocketTimeoutException
from java.io  import IOException
from java.sql import SQLException

try:
    ...
except UnknownHostException as error:
    ...
except SQLException as error:
    ...
```

Na JVM, os dois sistemas de exceções são o mesmo sistema.

### 8. Terminal em UTF-8 com `java.io`

```python
STDOUT = PrintWriter(OutputStreamWriter(System.out, "UTF-8"), True)
STDIN  = BufferedReader(InputStreamReader(getattr(System, "in"), "UTF-8"))
```

Repare no `getattr(System, "in")`: `System.in` não pode ser escrito
diretamente porque `in` é uma **palavra reservada do Python**.

---

## APIs Java utilizadas

| Classe / API                        | Onde                              | Finalidade                                    |
| ----------------------------------- | --------------------------------- | --------------------------------------------- |
| `java.net.URL`                      | `groq_client.py`                  | Endereço do endpoint da Groq                  |
| `java.net.HttpURLConnection`        | `groq_client.py`                  | POST HTTPS e códigos de status                |
| `java.net.UnknownHostException`     | `groq_client.py`                  | Detectar falta de internet / falha de DNS     |
| `java.net.ConnectException`         | `groq_client.py`                  | Detectar recusa de conexão                    |
| `java.net.SocketTimeoutException`   | `groq_client.py`                  | Detectar timeout                              |
| `java.io.OutputStreamWriter`        | `groq_client.py`, `main.py`       | Enviar o JSON; saída em UTF-8                 |
| `java.io.InputStreamReader`         | `groq_client.py`, `main.py`       | Ler resposta HTTP e teclado em UTF-8          |
| `java.io.BufferedReader`            | `groq_client.py`, `main.py`       | Processar resposta e ler a linha digitada     |
| `java.io.PrintWriter`               | `main.py`                         | Escrever no terminal                          |
| `java.io.File` / `FileInputStream`  | `tools/knowledge_tool.py`         | Listar e ler os Markdown da base              |
| `java.io.IOException`               | `groq_client.py`                  | Tratamento de falhas de entrada/saída         |
| `java.lang.System`                  | vários                            | `getenv()`, `getProperty()`, `currentTimeMillis()`, `out`, `err`, `in` |
| `java.lang.StringBuilder`           | `groq_client.py`                  | Concatenar a resposta lida                    |
| `java.lang.Thread`                  | `groq_client.py`                  | Espera entre tentativas em HTTP 429           |
| `java.lang.Class`                   | `database/connection.py`          | Carregar o driver `org.sqlite.JDBC`           |
| `java.util.ArrayList`               | `chat.py`                         | Contexto da conversa                          |
| `java.util.LinkedHashMap`           | `chat.py`                         | Cada mensagem (`role` + `content`)            |
| `java.util.Collections`             | `chat.py`                         | Ordenação e visão somente-leitura             |
| `java.util.UUID`                    | `tests/test_database.py`          | Nome único do banco temporário                |
| `java.text.Normalizer`              | `search/normalizer.py`            | Remoção de acentos (NFD)                      |
| `java.time.LocalDateTime`           | `database/interaction_repository.py` | Data/hora dos registros                    |
| `java.sql.DriverManager`            | `database/connection.py`          | Abrir a conexão JDBC                          |
| `java.sql.PreparedStatement`        | `database/connection.py`          | SQL parametrizado                             |
| `java.sql.ResultSet`                | `database/connection.py`          | Leitura dos resultados                        |
| `java.sql.SQLException`             | `database/connection.py`          | Erros de banco                                |
| `org.apache.commons.text.similarity.JaroWinklerSimilarity` | `search/fuzzy_matcher.py` | Similaridade textual        |
| `org.apache.commons.text.similarity.LevenshteinDistance`   | `search/fuzzy_matcher.py` | Distância de edição         |

---

## As seis ferramentas do agente

| Ferramenta | Quando o modelo usa | O que devolve |
| --- | --- | --- |
| `search_project_knowledge` | Perguntas sobre o projeto | Trechos da documentação local com score |
| `list_project_tests` | "quais testes existem?" | Catálogo T01..T15 + T90 |
| `run_project_tests` | "rode os testes de fuzzy" | Passaram / falharam / tempo / detalhes |
| `search_chat_history` | "já falamos sobre X?" | Conversas antigas relevantes |
| `get_recent_interactions` | "sobre o que conversamos?" | Últimas interações |
| `get_usage_metrics` | "quantos tokens usamos?" | Tokens, cache, latência, uso de tools |

O modelo **nunca executa código arbitrário**. O registro
(`tools/registry.py`) mantém uma lista branca com esses seis nomes e valida os
argumentos contra o schema declarado antes de executar. Não há `eval`, `exec`,
shell nem `subprocess` dirigido pelo modelo — se vier `delete_everything`, o
resultado é `Ferramenta inexistente` e nada roda.

---

## Estrutura do projeto

```text
jython-ai-agent/
│
├── README.md              este guia
├── Dockerfile             build em dois estágios (Maven + runtime)
├── pom.xml                dependências Java
├── .env.example           modelo de configuração
├── .gitignore             protege o .env
├── .dockerignore          mantém o .env fora da imagem
│
├── main.py                terminal e bootstrap
├── config.py              configuração via java.lang.System.getenv()
├── chat.py                contexto em java.util.ArrayList
├── groq_client.py         HTTP via java.net + java.io
├── orchestrator.py        agentic loop
│
├── database/              SQLite via JDBC
│   ├── connection.py
│   ├── schema.py
│   ├── interaction_repository.py
│   └── metrics_repository.py
│
├── tools/                 as seis ferramentas
│   ├── registry.py
│   ├── knowledge_tool.py
│   ├── tests_tool.py
│   ├── history_tool.py
│   └── metrics_tool.py
│
├── search/                RAG lexical
│   ├── normalizer.py
│   ├── chunker.py
│   └── fuzzy_matcher.py
│
├── knowledge/             8 documentos consultáveis pelo agente
├── tests/                 suíte T01..T15 + T90
├── docs/
│   ├── PROJECT_GUIDE.md   arquitetura completa (23 seções)
│   └── LLM_AND_TOOLS.md   funcionamento da IA
```

---

## Pré-requisitos

```text
Docker
Uma chave da API da Groq (gratuita)
```

Nada mais. **Não é preciso instalar Python, Jython, Java ou Maven na máquina**:
o build baixa tudo.

Tecnologias fixadas:

```text
Jython             : 2.7.4
Java               : 11 (Eclipse Temurin)
SQLite JDBC        : 3.53.4.0 (Xerial)
Apache Commons Text: 1.15.0
API                : Groq Chat Completions
Modelo             : openai/gpt-oss-120b
```

---

## Obtendo uma API Key da Groq

1. Acesse <https://console.groq.com/keys>
2. Faça login (a criação de conta é gratuita).
3. Clique em **Create API Key**, dê um nome e copie a chave gerada.
4. Guarde a chave: ela começa com `gsk_` e só é exibida uma vez.

A documentação da Groq recomenda **não** colocar a chave no código, e sim usar
variáveis de ambiente — que é exatamente o que este projeto faz, através de
`java.lang.System.getenv()`.

---

## Configuração do `.env`

Copie o modelo:

```bash
# Linux / macOS
cp .env.example .env
```

```powershell
# Windows (PowerShell)
Copy-Item .env.example .env
```

E edite o `.env` com a sua chave:

```env
GROQ_API_KEY=gsk_sua_chave_aqui
GROQ_MODEL=openai/gpt-oss-120b
```

O programa **nunca lê o `.env` diretamente** e ele **nunca entra na imagem
Docker**. Quem o lê é o próprio Docker, que injeta as variáveis no container:

```text
.env
 │
 │  docker run --env-file .env
 ▼
Container
 │
 │  variável de ambiente
 ▼
java.lang.System.getenv("GROQ_API_KEY")
 │
 ▼
Jython
```

Variáveis aceitas (todas com valor padrão, exceto a chave):

| Variável | Padrão |
| --- | --- |
| `GROQ_API_KEY` | *(obrigatória)* |
| `GROQ_MODEL` | `openai/gpt-oss-120b` |
| `GROQ_API_URL` | `https://api.groq.com/openai/v1/chat/completions` |
| `GROQ_TEMPERATURE` | `1.0` (recomendado para o gpt-oss) |
| `GROQ_REASONING_EFFORT` | `medium` (low, medium ou high) |
| `GROQ_MAX_TOKENS` | `1500` |
| `GROQ_MAX_RETRIES` | `3` |
| `GROQ_SYSTEM_PROMPT` | prompt padrão em português |
| `AGENT_MAX_ITERATIONS` | `5` |
| `AGENT_CONTEXT_TURNS` | `4` |
| `DATABASE_PATH` | `/app/data/jython_ai_chat.db` |
| `KNOWLEDGE_DIR` | `/app/knowledge` |
| `KNOWLEDGE_TOP_K` | `3` |
| `KNOWLEDGE_MIN_SCORE` | `0.35` |
| `HISTORY_SEARCH_LIMIT` | `5` |
| `GROQ_CONNECT_TIMEOUT_MS` | `15000` |
| `GROQ_READ_TIMEOUT_MS` | `120000` |

---

## Executando com Docker

### 1. Construir a imagem

```bash
docker build -t jython-ai-agent .
```

O primeiro estágio usa Maven para baixar `jython-standalone`, `sqlite-jdbc` e
`commons-text`; o segundo monta a imagem final apenas com o Java 11, os JARs e
o código.

### 2. Criar o volume de dados

```bash
docker volume create jython-ai-data
```

Sem ele, o histórico e as métricas somem quando o container é removido pelo
`--rm`.

### 3. Executar o agente

```bash
docker run --rm -it --env-file .env -v jython-ai-data:/app/data jython-ai-agent
```

O `-it` é obrigatório: o agente é interativo. Se for esquecido, o programa
avisa em vez de quebrar.

Como o `ENTRYPOINT` é o Jython e o `CMD` é apenas o nome do script, o mesmo
container roda qualquer arquivo do projeto:

```bash
# o agente (padrão)
docker run --rm -it --env-file .env -v jython-ai-data:/app/data jython-ai-agent

# suíte de testes, direto pela linha de comando
docker run --rm jython-ai-agent -c "from tests import registry; r = registry.run('all'); print('%s/%s passaram em %s ms' % (r['passaram'], r['executados'], r['tempo_ms']))"
```

---

## Utilizando o agente

Comandos do terminal:

| Comando  | Efeito                                                  |
| -------- | ------------------------------------------------------- |
| `/help`  | Mostra a ajuda e exemplos de perguntas                  |
| `/info`  | Runtime, banco, conhecimento e classes Java em uso      |
| `/tools` | Lista as seis ferramentas registradas                   |
| `/clear` | Limpa o contexto em memória (o banco continua intacto)  |
| `/exit`  | Encerra o programa (`/quit` e `/sair` também)           |

### Perguntando sobre o próprio projeto

```text
Você: como esse projeto faz a comunicação com a Groq?

[consultando o conhecimento do projeto... 42 ms]

Assistente:
O projeto se comunica com a Groq usando a Chat Completions API. A classe
groq_client.py utiliza as APIs de rede da JVM: java.net.URL cria o endereço,
HttpURLConnection abre a conexão HTTPS e define o método POST,
OutputStreamWriter grava o corpo JSON e a resposta é lida com
InputStreamReader e BufferedReader...

   [5.5s | 2 chamada(s) LLM | tools: search_project_knowledge | 2771 tokens]
```

### Executando testes pela conversa

```text
Você: rode os testes de fuzzy

[executando os testes... 495 ms]

Assistente:
Foram executados os testes de fuzzy. Todos os 4 testes passaram:

- T08 – Busca fuzzy com correspondência exata
- T09 – Busca fuzzy com erro de digitação
- T10 – Knowledge Search respeita top_k
- T14 – Busca fuzzy no histórico de conversas

Tempo total: 422 ms. Nenhum erro foi encontrado.

   [1.9s | 2 chamada(s) LLM | tools: run_project_tests | 1402 tokens]
```

### Consultando métricas

```text
Você: quantos tokens já usamos nesta sessão e qual a taxa de cache?

[consultando as métricas de uso... 3 ms]

Assistente:
Nesta sessão foram feitas 3 chamadas ao modelo. O total de tokens de entrada
foi 3810 (média de 1270 por chamada) e o total de saída foi 220 (média 73).
A taxa de acerto do cache foi 0%. A latência média foi cerca de 605 ms.

   [1.1s | 2 chamada(s) LLM | tools: get_usage_metrics | 1845 tokens]
```

### Lembrando de conversas antigas — inclusive de outro container

```text
Você: eu já falei sobre fuzzy antes? o que foi conversado?

[pesquisando o histórico de conversas... 19 ms]

Assistente:
Sim, você já mencionou fuzzy em interações anteriores.

- Na conversa das 20:06, você pediu para rodar os testes de fuzzy. Executei os
  testes e informei que foram quatro (T08, T09, T10 e T14) e que todos
  passaram, com tempo total de 422 ms.
- Pouco antes, às 20:04, você fez outro pedido semelhante.

   [1.8s | 2 chamada(s) LLM | tools: search_chat_history | 1656 tokens]
```

Essa última resposta veio de um **container diferente** daquele que gravou as
conversas: o banco vive no volume `jython-ai-data`.

---

## Testes automatizados

São 15 testes offline (não gastam tokens) e 1 de integração.

```text
T01  Configuração padrão do modelo
T02  Histórico usa java.util.ArrayList
T03  Adição de mensagens user/assistant
T04  Limpeza do contexto preserva o system prompt
T05  Payload da Groq inclui as tools
T06  Parser reconhece tool_calls
T07  Tool Registry valida a lista branca
T08  Busca fuzzy com correspondência exata
T09  Busca fuzzy com erro de digitação
T10  Knowledge Search respeita top_k
T11  SQLite cria todas as tabelas
T12  Interação é salva corretamente
T13  Métricas de tokens, cache e latência
T14  Busca fuzzy no histórico de conversas
T15  Janela de contexto deslizante

T90  Integração real com a Groq (fora da execução padrão)
```

Execução direta:

```bash
docker run --rm jython-ai-agent -c "from tests import registry; r = registry.run('all'); print('%s/%s passaram em %s ms' % (r['passaram'], r['executados'], r['tempo_ms']))"
```

Saída real:

```text
14/14 passaram em 844 ms
```

Ou pela conversa: *"rode todos os testes"*, *"rode os testes de banco"*,
*"execute T08 e T09"*.

Os testes de banco criam arquivos temporários com nome baseado em
`java.util.UUID` dentro de `java.io.tmpdir` e os apagam ao final — o banco de
produção nunca é tocado. O T90 é o único que chama a Groq de verdade e só roda
quando pedido explicitamente.

O T09 é o mais divertido de mostrar: a pergunta

```text
"como confguro o doker pra roda jyton?"
```

ainda encontra `08_docker_configuration.md`, porque `doker ~ docker` tem
similaridade de Jaro-Winkler 0.9556 e `jyton ~ jython`, 0.9611.

---

## Persistência e métricas

Cinco tabelas deixam a execução inteiramente auditável:

```text
sessions          uma linha por execução do programa
interactions      uma linha por pergunta completa
messages          uma linha por mensagem (system/user/assistant/tool)
llm_calls         uma linha por chamada à Groq
tool_executions   uma linha por ferramenta executada
```

Conteúdo real do banco após alguns minutos de uso:

```text
tabelas: interactions, llm_calls, messages, sessions, tool_executions
  sessions         5 linhas
  interactions     9 linhas
  messages         33 linhas
  llm_calls        15 linhas
  tool_executions  9 linhas

--- llm_calls ---
  int=9 idx=1 in=2534 out=53  cache=0   groq=241ms local=489ms finish=stop
  int=9 idx=0 in=2267 out=72  cache=256 groq=253ms local=616ms finish=tool_calls
  int=8 idx=1 in=2069 out=285 cache=0   groq=678ms local=944ms finish=stop
  int=8 idx=0 in=1075 out=150 cache=0   groq=380ms local=862ms finish=tool_calls

--- tool_executions ---
  get_recent_interactions    1 execuções | 1 ok |   2.0 ms média
  get_usage_metrics          2 execuções | 2 ok |   3.5 ms média
  list_project_tests         2 execuções | 2 ok |   0.5 ms média
  run_project_tests          2 execuções | 2 ok | 505.5 ms média
  search_chat_history        1 execuções | 1 ok |  19.0 ms média
  search_project_knowledge   1 execuções | 1 ok |  42.0 ms média
```

Repare no `cache=256`: é o **prompt caching da Groq** funcionando, porque o
prompt de sistema e os schemas das ferramentas são mantidos estáveis entre as
requisições.

---

### O banco como ferramenta de diagnóstico

Essa observabilidade não é enfeite: ela foi usada para achar um bug real. O
agente começou a responder com lixo depois de algumas perguntas parecidas em
sequência, e a consulta abaixo mostrou o custo de cada chamada:

```sql
SELECT interaction_id, call_index, prompt_tokens, completion_tokens,
       cached_tokens, http_attempts, finish_reason
FROM llm_calls ORDER BY id DESC LIMIT 10;
```

Os números apontaram duas coisas: o contexto crescia sem limite (cada pergunta
ficava mais cara que a anterior, até estourar o limite de tokens por minuto) e
o modelo degenerava em repetição. O diagnóstico completo — com as hipóteses
testadas e descartadas — está em
[docs/LLM_AND_TOOLS.md](docs/LLM_AND_TOOLS.md), seção 13. As correções foram:

| Correção | Efeito |
| --- | --- |
| Reenviar o campo `reasoning` do gpt-oss no histórico | Respostas limpas em 4 de 4 rodadas (antes: 1 de 4) |
| `temperature` de 0.4 para 1.0 (recomendado para o modelo) | Fim do colapso por repetição |
| Janela de contexto deslizante (`AGENT_CONTEXT_TURNS`) | Tokens por interação de ~4.400 para ~1.650 |
| Resultados de ferramenta mais enxutos | Menos pressão no limite por minuto |
| `llm_calls.http_attempts` e `retry_wait_ms` | Os HTTP 429 agora ficam auditáveis |

Resultado no mesmo roteiro de quatro perguntas seguidas: nenhum HTTP 429, de
1,1 s a 1,4 s por resposta (antes: 21 s a 34 s) e 1.024 tokens de cache
aproveitados em todas as chamadas.

---

## Tratamento de erros

O programa nunca mostra *stack trace* ao usuário: toda falha vira uma mensagem
explicando o que aconteceu e o que fazer. Todas as saídas abaixo são reais.

### Chave ausente

```text
[ERRO] GROQ_API_KEY não encontrada.

A chave é lida do ambiente por java.lang.System.getenv("GROQ_API_KEY").

Crie o arquivo .env na raiz do projeto:

    GROQ_API_KEY=gsk_sua_chave_aqui
    GROQ_MODEL=openai/gpt-oss-120b
```

### Chave inválida (HTTP 401)

```text
[ERRO] Não foi possível autenticar na Groq (HTTP 401).
       Verifique sua GROQ_API_KEY.
       Detalhe da API: Invalid API Key
```

### Limite de requisições (HTTP 429) — com repetição automática

```text
[a Groq respondeu HTTP 429; aguardando 10.6s antes da tentativa 2]
```

A Groq informa quanto esperar na própria mensagem de erro; o cliente lê esse
tempo e repete a chamada usando `java.lang.Thread.sleep`. Só depois de esgotar
`GROQ_MAX_RETRIES` a mensagem de erro chega ao usuário.

### Sem internet / DNS falhando

```text
[ERRO] Não foi possível conectar à API da Groq.
       O endereço api.groq.com não pôde ser resolvido.
       Verifique sua conexão com a internet.
```

*(`java.net.UnknownHostException` capturada por um `except` de Python.)*

### Ferramenta inexistente pedida pelo modelo

```text
{"error": "Ferramenta inexistente: delete_everything",
 "ferramentas_disponiveis": ["search_project_knowledge", "..."]}
```

Nada é executado — o erro volta ao modelo, que se corrige.

### Limite de iterações do agente

```text
[ERRO] Limite de execução de ferramentas atingido (5 iterações).
       Reformule a pergunta ou aumente AGENT_MAX_ITERATIONS.
```

### Banco de dados indisponível

O agente **continua funcionando** sem histórico e sem métricas; apenas as
ferramentas dependentes avisam que o banco está desligado.

### Terminal não interativo (esqueceu o `-it`)

```text
[aviso] Nenhuma entrada disponível no terminal.
        O agente é interativo: execute o container com -it
```

---

## Segurança da API Key

| Local                        | Contém a chave? |
| ---------------------------- | --------------- |
| `main.py`, `config.py`       | Não             |
| `Dockerfile`, `pom.xml`      | Não             |
| `README.md`                  | Não             |
| Imagem Docker                | Não             |
| GitHub                       | Não             |
| `.env` local                 | **Sim**         |

Camadas de proteção:

1. `.gitignore` — o `.env` nunca é versionado.
2. `.dockerignore` — o `.env` nunca entra no contexto do build; além disso, o
   `Dockerfile` copia diretórios explícitos, e não `COPY . .`.
3. A chave só existe dentro do container em tempo de execução, injetada por
   `--env-file .env` e lida por `System.getenv()`.
4. No terminal, a chave sempre aparece mascarada (`gsk_********KdLl`).

Além disso, o container roda com usuário sem privilégios (`chat`, uid 10001),
todo SQL usa `PreparedStatement` parametrizado e o modelo só pode executar os
seis nomes da lista branca.

Se uma chave for exposta por acidente, revogue-a em
<https://console.groq.com/keys> e gere outra.

---

## Executando sem Docker (opcional)

É preciso ter Java 8/11 e os três JARs (`jython-standalone-2.7.4.jar`,
`sqlite-jdbc`, `commons-text` e sua dependência `commons-lang3`). O Maven
resolve tudo:

```bash
mvn -B dependency:copy-dependencies -DoutputDirectory=lib -DincludeScope=runtime
```

Depois:

```bash
# Linux / macOS
export GROQ_API_KEY=gsk_sua_chave
java -cp "lib/*:." org.python.util.jython main.py
```

```powershell
# Windows (PowerShell)
$env:GROQ_API_KEY = "gsk_sua_chave"
java -cp "lib/*;." org.python.util.jython main.py
```

Sem chave, a suíte de testes ainda roda:

```bash
docker run --rm jython-ai-agent -c "from tests import registry; r = registry.run('all'); print('%s/%s passaram em %s ms' % (r['passaram'], r['executados'], r['tempo_ms']))"
```

O caminho recomendado continua sendo o Docker: ele dispensa qualquer instalação
na máquina.

---

## Documentação técnica

| Documento | Conteúdo |
| --- | --- |
| [docs/PROJECT_GUIDE.md](docs/PROJECT_GUIDE.md) | Arquitetura completa em 23 seções: motivações, fluxos, GroqClient, registry, knowledge base, algoritmo fuzzy, SQLite, tabelas, métricas, cache, testes, Docker, segurança, limitações e evoluções. |
| [docs/LLM_AND_TOOLS.md](docs/LLM_AND_TOOLS.md) | A camada de IA: modelo, system prompt, tool schemas, agentic loop, recuperação de conhecimento, tokens, cache, limite de iterações e tratamento de alucinação. |
| [knowledge/](knowledge/) | Os 8 documentos que o próprio agente consulta. |

---

## Demonstração

Vídeo de apresentação (até 5 minutos):

> **Link do vídeo:** _(adicione aqui o link do Loom)_

Roteiro sugerido:

```text
0:00 - 0:30   Apresentação do projeto
0:30 - 1:10   O que é Jython e a diferença para o CPython
1:10 - 1:50   Os imports Java dentro dos arquivos .py
1:50 - 2:30   groq_client.py (java.net/java.io) e database (java.sql)
2:30 - 3:00   Dockerfile, classpath e injeção do .env
3:00 - 4:20   Executando: conhecimento, testes, histórico e métricas
4:20 - 5:00   Interoperabilidade e conclusão
```

Comandos da demonstração:

```bash
docker build -t jython-ai-agent .
docker volume create jython-ai-data
docker run --rm -it --env-file .env -v jython-ai-data:/app/data jython-ai-agent
```

Perguntas que mostram tudo funcionando:

```text
como esse projeto usa Jython?          -> search_project_knowledge
quais testes eu posso executar?        -> list_project_tests
rode os testes de fuzzy                -> run_project_tests
eu já falei sobre fuzzy antes?         -> search_chat_history
quantos tokens já usamos?              -> get_usage_metrics
```

---

## Autor

_Thalia de Oliveira Santos_

Projeto desenvolvido para a disciplina **Paradigmas de Linguagens de
Programação** (2026.2) — Prof. Thiago Sales.

---
## Link do vídeo explicativo do projeto
[Projeto PLP explicando — YouTube](https://youtu.be/wu0MpKKdosI)

## Referências

- [Jython — site oficial](https://www.jython.org/)
- [Jython 2.7.4 no Maven Central](https://repo1.maven.org/maven2/org/python/jython-standalone/2.7.4/)
- [Groq — API Reference](https://console.groq.com/docs/api-reference)
- [Groq — Tool Use / Function Calling](https://console.groq.com/docs/tool-use)
- [Groq — Prompt Caching](https://console.groq.com/docs/prompt-caching)
- [Groq — modelo openai/gpt-oss-120b](https://console.groq.com/docs/model/openai/gpt-oss-120b)
- [Apache Commons Text — similarity](https://commons.apache.org/proper/commons-text/apidocs/org/apache/commons/text/similarity/package-summary.html)
- [SQLite JDBC (Xerial)](https://github.com/xerial/sqlite-jdbc)
- [Caelum Stella](https://github.com/caelum/caelum-stella)
- [Caelum Stella Core 2.2.2](https://central.sonatype.com/artifact/br.com.caelum.stella/caelum-stella-core/2.2.2)
