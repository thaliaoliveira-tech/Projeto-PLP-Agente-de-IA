# PROJECT_GUIDE — Arquitetura do Jython AI Agent

Documento técnico completo do projeto. O `README.md` é o guia de instalação e
uso; este arquivo explica **como e por que** o projeto foi construído assim.

---

## Caelum Stella

`stella/` encapsula `caelum-stella-core:2.2.2` com um catálogo estático,
seis tools semânticas e auditoria redigida. `/stella` é o modo local que não
chama a Groq.

## 1. Objetivo do projeto

Demonstrar, de forma concreta, a interoperabilidade entre Python e Java quando
as duas linguagens compartilham a mesma plataforma de execução — a JVM.

O produto é um **assistente técnico agentivo de terminal**: o usuário conversa
em português, o modelo `openai/gpt-oss-120b` (servido pela Groq) decide se
consegue responder sozinho ou se precisa de uma ferramenta local, e a
aplicação executa essa ferramenta, devolve o resultado ao modelo e imprime a
resposta final.

A regra que orienta todas as decisões técnicas: **nenhuma biblioteca Python
pode esconder a plataforma Java**. Não há `requests`, `urllib`, `httplib`,
`sqlite3`, `groq` nem `openai`. Rede, streams, coleções, banco de dados,
normalização Unicode e similaridade textual são resolvidos com classes e
bibliotecas Java chamadas diretamente do código Python.

---

## 2. Arquitetura

```text
                        ┌─────────────────────┐
                        │       Usuário       │
                        │      (terminal)     │
                        └──────────┬──────────┘
                                   │ java.io.BufferedReader
                                   ▼
                        ┌─────────────────────┐
                        │     main.py         │
                        │  banner, comandos   │
                        └──────────┬──────────┘
                                   ▼
                        ┌─────────────────────┐
                        │  orchestrator.py    │
                        │   agentic loop      │
                        └──────────┬──────────┘
                                   │
                    ┌──────────────┴───────────────┐
                    ▼                              ▼
         ┌─────────────────────┐        ┌─────────────────────┐
         │   groq_client.py    │        │  tools/registry.py  │
         │ java.net + java.io  │        │   lista branca      │
         └──────────┬──────────┘        └──────────┬──────────┘
                    │ HTTPS                        │
                    ▼                              │
         ┌─────────────────────┐                   │
         │      GROQ API       │                   │
         │ openai/gpt-oss-120b │                   │
         └─────────────────────┘                   │
                                                   │
             ┌─────────────────────┬───────────────┴───────┐
             ▼                     ▼                       ▼
     Knowledge Tool          Testing Tool          Observability Tools
             │                     │                       │
      busca fuzzy             unittest              SQLite via JDBC
             │                     │                       │
      knowledge/*.md           tests/            histórico + métricas
```

Há **um único LLM orquestrador** e **seis ferramentas determinísticas**. Os
"três agentes" do desenho conceitual (conhecimento, testes, observabilidade)
são áreas de responsabilidade, não instâncias separadas de IA: isso reduz
tokens, reduz latência, é mais simples de explicar e deixa o comportamento
testável.

---

## 3. Motivações das escolhas

| Decisão | Motivo |
| --- | --- |
| `java.net.HttpURLConnection` em vez de `requests` | O objetivo da atividade é usar APIs Java; uma biblioteca Python esconderia exatamente o que se quer demonstrar. |
| JDBC em vez de `sqlite3` | Mesma razão, agora no subsistema de dados: `java.sql` é a API padrão de banco da plataforma Java. |
| Apache Commons Text em vez de `difflib` | Traz uma **biblioteca Java de terceiros** para dentro do código Python, além das APIs padrão. |
| Busca lexical em vez de embeddings | Sem serviço externo de vetores, sem custo extra e com resultado explicável: dá para mostrar o score de cada trecho. |
| Um orquestrador com 6 tools em vez de 3 LLMs | Menos tokens, menos latência, comportamento determinístico e testável. |
| Lista branca de ferramentas | O modelo nunca executa código arbitrário; sem `eval`, `exec` ou `subprocess`. |
| Limite de iterações | Evita laços infinitos de chamadas de ferramenta. |
| Volume Docker para o banco | O histórico e as métricas sobrevivem à remoção do container. |

---

## 4. CPython comparado ao Jython

|                               | CPython               | Jython                 |
| ----------------------------- | --------------------- | ---------------------- |
| Escrito em                    | C                     | Java                   |
| Executa sobre                 | Interpretador próprio | JVM                    |
| Compila para                  | bytecode CPython      | **bytecode Java**      |
| Usa bibliotecas Java          | Não                   | **Sim, nativamente**   |
| Usa extensões C (NumPy, etc.) | Sim                   | Não                    |
| Versão da linguagem           | 3.x                   | 2.7                    |

Consequências práticas dentro do projeto:

- `import` procura primeiro nos módulos Python; para o pacote `java`, delega
  ao *classloader* da JVM.
- Os tipos são convertidos automaticamente: `unicode` ↔ `java.lang.String`,
  `bool` ↔ `boolean`, `None` ↔ `null`, `int` ↔ `Integer`/`Long`.
- Um `for` de Python itera sobre um `java.util.ArrayList` sem adaptação.
- Uma exceção lançada por código Java é capturada por um `except` de Python.
- `System.in` precisa de `getattr(System, "in")`, porque `in` é palavra
  reservada do Python — o encontro literal das duas gramáticas.

---

## 5. Estrutura de diretórios

```text
jython-ai-agent/
│
├── README.md              guia de instalação e uso
├── Dockerfile             build em dois estágios (Maven + runtime)
├── pom.xml                dependências Java (Jython, JDBC, Commons Text)
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
│   ├── connection.py      conexão, PreparedStatement, ResultSet
│   ├── schema.py          DDL das cinco tabelas
│   ├── interaction_repository.py
│   └── metrics_repository.py
│
├── tools/                 as seis ferramentas do agente
│   ├── registry.py        lista branca, validação e despacho
│   ├── knowledge_tool.py  search_project_knowledge
│   ├── tests_tool.py      list_project_tests, run_project_tests
│   ├── history_tool.py    search_chat_history, get_recent_interactions
│   └── metrics_tool.py    get_usage_metrics
│
├── search/                RAG lexical
│   ├── normalizer.py      java.text.Normalizer
│   ├── chunker.py         quebra dos Markdown em trechos
│   └── fuzzy_matcher.py   Apache Commons Text
│
├── knowledge/             8 documentos consultáveis pelo agente
├── tests/                 suíte T01..T15 + T90
└── docs/                  PROJECT_GUIDE.md e LLM_AND_TOOLS.md
```

---

## 6. Responsabilidade de cada arquivo

| Arquivo | Responsabilidade |
| --- | --- |
| `main.py` | Terminal (entrada/saída em UTF-8 por `java.io`), banner, comandos `/help`, `/info`, `/tools`, `/clear`, `/exit`, bootstrap de banco, conhecimento, ferramentas e orquestrador. |
| `orchestrator.py` | O agentic loop: chama a LLM, executa ferramentas, grava tudo, respeita o limite de iterações. |
| `groq_client.py` | Monta o JSON, faz o POST HTTPS por `HttpURLConnection`, interpreta `content` e `tool_calls`, traduz erros e repete chamadas temporariamente falhas. |
| `chat.py` | Contexto da conversa em `java.util.ArrayList` de `java.util.LinkedHashMap`, incluindo mensagens de papel `tool`. |
| `config.py` | Lê todas as variáveis de ambiente por `java.lang.System.getenv()` e valida a configuração mínima. |
| `tools/registry.py` | Lista branca, validação de argumentos contra o schema e despacho seguro. |
| `tools/knowledge_tool.py` | Carrega `knowledge/*.md` com `java.io` e responde `search_project_knowledge`. |
| `tools/tests_tool.py` | Expõe a suíte de testes ao agente. |
| `tools/history_tool.py` | Busca fuzzy e listagem do histórico gravado. |
| `tools/metrics_tool.py` | Estatísticas de tokens, cache, latência e ferramentas. |
| `search/normalizer.py` | Minúsculas, remoção de acentos (`java.text.Normalizer`) e tokenização. |
| `search/chunker.py` | Divide cada Markdown em trechos de 500 a 1.000 caracteres. |
| `search/fuzzy_matcher.py` | Score combinado com `JaroWinklerSimilarity` e `LevenshteinDistance`. |
| `database/connection.py` | Conexão JDBC, `PreparedStatement`, `ResultSet` e criação do schema. |
| `database/interaction_repository.py` | Sessões, interações, mensagens, chamadas à LLM e execuções de ferramenta. |
| `database/metrics_repository.py` | Agregações SQL (COUNT, SUM, AVG, MIN, MAX) e taxa de cache. |
| `tests/registry.py` | Catálogo T01..T15 + T90 e executor com resultado estruturado. |

---

## 7. Fluxo completo de uma mensagem

```text
 1. java.io.BufferedReader lê a linha digitada
 2. main.py entrega o texto ao orquestrador
 3. o orquestrador abre uma interação no SQLite
 4. a pergunta vira java.util.LinkedHashMap dentro do ArrayList do histórico
 5. a pergunta é gravada na tabela messages
 6. groq_client monta o JSON: histórico + 6 tool schemas
 7. java.net.URL + HttpURLConnection abrem o POST HTTPS
 8. java.io.OutputStreamWriter escreve o JSON no socket
 9. a Groq responde; InputStreamReader + BufferedReader leem
10. java.lang.StringBuilder monta o texto recebido
11. json.loads devolve content OU tool_calls
12. a chamada é gravada em llm_calls (tokens, cache, tempos)
13. havendo tool_calls -> ver seção 8; senão, a resposta é final
14. a resposta entra no ArrayList e na tabela messages
15. a interação é fechada com o tempo total
16. java.io.PrintWriter imprime no terminal
```

---

## 8. Fluxo de tool calling

```text
modelo devolve tool_calls
        │
        ▼
registry.execute(nome, argumentos)
        │
        ├── nome fora da lista branca? -> erro controlado, nada executa
        ├── argumentos não são objeto JSON? -> erro controlado
        ├── falta parâmetro obrigatório? -> erro controlado
        ├── tipo errado? -> coerção ou erro controlado
        │
        ▼
handler Python roda localmente (busca, testes, SQL...)
        │
        ▼
resultado vira JSON, é truncado em 3.500 caracteres
        │
        ├── gravado em tool_executions (argumentos, resultado, duração, sucesso)
        ├── inserido no histórico como mensagem role="tool" + tool_call_id
        │
        ▼
nova chamada à Groq com o histórico já contendo o resultado
        │
        ▼
repete até vir conteúdo textual ou atingir AGENT_MAX_ITERATIONS
```

O usuário nunca vê o JSON cru: o terminal mostra apenas uma linha de
progresso, como `[consultando o conhecimento do projeto... 42 ms]`, e depois a
resposta em linguagem natural.

---

## 9. GroqClient

`GroqClient` é o único ponto do projeto que fala com a rede.

Requisição:

```python
url = URL(self.api_url)                    # java.net.URL
connection = url.openConnection()          # java.net.HttpURLConnection
connection.setRequestMethod("POST")
connection.setRequestProperty("Authorization", "Bearer " + self.api_key)
connection.setDoOutput(True)

writer = OutputStreamWriter(connection.getOutputStream(), "UTF-8")
writer.write(payload)
```

Resposta, já normalizada em objetos Python:

```text
GroqReply
├── content          texto final (ou None quando houve tool_calls)
├── reasoning        o raciocínio do gpt-oss (volta ao histórico -- seção 9.1)
├── tool_calls       lista de ToolCall
├── finish_reason    stop | tool_calls | length
├── model
├── usage            tokens, cached_tokens e tempos da Groq
├── attempts         quantas requisições HTTP foram necessárias
├── retry_wait_ms    quanto tempo o cliente esperou por causa de 429/5xx
└── elapsed_ms       medido com System.currentTimeMillis()

ToolCall
├── id
├── name
└── arguments        já convertidos de JSON para dict
```

Erros temporários (HTTP 429 e 5xx) são repetidos automaticamente: a mensagem
da Groq costuma dizer quanto esperar (`try again in 5.15s`), e o cliente
respeita esse tempo usando `java.lang.Thread.sleep`. `GROQ_MAX_RETRIES`
controla quantas repetições são aceitas, e o número de tentativas fica gravado
em `llm_calls.http_attempts`.

### 9.1 O raciocínio volta ao histórico

O `gpt-oss` devolve o raciocínio em um campo `reasoning`, separado do texto
final. Esse campo **precisa** ser reenviado na mensagem que pediu ferramentas:
sem ele, o modelo perde a própria linha de raciocínio e degenera em repetição
depois de algumas rodadas parecidas. O diagnóstico completo, com as hipóteses
descartadas e os números antes/depois, está em
[LLM_AND_TOOLS.md](LLM_AND_TOOLS.md), seção 13.

---

## 10. Tool Registry

O registro é a fronteira de segurança do projeto. Ele guarda:

```text
Tool
├── name          nome exposto ao modelo
├── description   instrução de quando usar
├── parameters    JSON Schema dos argumentos
├── required      parâmetros obrigatórios
└── handler       função Python que executa de fato
```

E aplica, em ordem: lista branca → argumentos são objeto JSON → obrigatórios
presentes → tipos corretos (com coerção simples e validação de `enum`).

Se o modelo pedir `delete_everything`, o resultado é
`{"error": "Ferramenta inexistente: delete_everything"}` — e nada roda. Esse
comportamento é verificado pelo teste T07.

---

## 11. Knowledge Base

Os oito arquivos de `knowledge/` são lidos com `java.io.File`,
`FileInputStream`, `InputStreamReader` e `BufferedReader`, e divididos em
trechos delimitados pelos títulos do Markdown, com 500 a 1.000 caracteres.

A base nunca é enviada inteira ao modelo. Por consulta vão, no máximo,
`KNOWLEDGE_TOP_K` trechos (3 por padrão), cada um limitado a
`KNOWLEDGE_MAX_CHARS` caracteres. Trechos com score abaixo de
`KNOWLEDGE_MIN_SCORE` são descartados.

```text
pergunta + ~3 trechos pequenos     em vez de     README + código inteiros
```

---

## 12. Algoritmo fuzzy

Normalização (`search/normalizer.py`): minúsculas, remoção de acentos com
`java.text.Normalizer` na forma NFD, pontuação virando separador e descarte de
*stopwords* do português.

```text
"configuração"  ->  NFD  ->  "configurac~ao"  ->  "configuracao"
```

Score (`search/fuzzy_matcher.py`):

```text
65%  similaridade por termos
25%  Jaro-Winkler entre a pergunta e o título/seção
10%  Levenshtein normalizado entre a pergunta e o título/seção
```

Na similaridade por termos, cada palavra da pergunta vale 1.0 se aparecer no
trecho (ou se for prefixo de uma palavra dele) e vale a própria similaridade
de Jaro-Winkler quando passa de 0.86 — é essa faixa que absorve erros de
digitação:

```text
doker    ~ docker        Jaro-Winkler 0.9556
jyton    ~ jython        Jaro-Winkler 0.9611
confguro ~ configuracao  Jaro-Winkler 0.9333
groq     ~ docker        Jaro-Winkler 0.4722   (não conta)
```

Por isso `"como confguro o doker pra roda jyton?"` ainda encontra
`08_docker_configuration.md` — comportamento fixado pelo teste T09.

---

## 13. SQLite

A persistência usa `java.sql` e o driver JDBC do SQLite (Xerial):

```python
from java.sql import DriverManager

JavaClass.forName("org.sqlite.JDBC")
connection = DriverManager.getConnection("jdbc:sqlite:/app/data/jython_ai_chat.db")
```

Todo SQL passa por `PreparedStatement` com parâmetros posicionais — nada de
concatenar strings — e os resultados são lidos de um `ResultSet` e convertidos
em dicionários Python. `java.io.File` cria o diretório do banco quando ele não
existe.

Se o banco falhar ao abrir, o agente **continua funcionando** sem histórico e
sem métricas: as ferramentas dependentes devolvem um erro amigável e o resto
da aplicação segue normalmente.

---

## 14. Estrutura das tabelas

```text
sessions              uma linha por execução do programa
├── id
├── started_at / finished_at
├── model
├── jython_version
└── java_version

interactions          uma linha por pergunta completa do usuário
├── id
├── session_id
├── started_at / finished_at
├── elapsed_ms
└── status            ok | error | limit | running

messages              uma linha por mensagem
├── id
├── session_id
├── interaction_id
├── role              system | user | assistant | tool
├── content
└── created_at

llm_calls             uma linha por chamada à Groq
├── id
├── interaction_id
├── call_index        0, 1, 2... dentro da mesma interação
├── model
├── prompt_tokens / completion_tokens / total_tokens
├── cached_tokens
├── queue_time_ms / prompt_time_ms / completion_time_ms
├── groq_total_time_ms
├── local_elapsed_ms
├── finish_reason
└── created_at

tool_executions       uma linha por ferramenta executada
├── id
├── interaction_id
├── tool_call_id
├── tool_name
├── arguments_json
├── result_json
├── elapsed_ms
├── success
├── error
└── created_at
```

Exemplo real, para a pergunta "como o projeto faz a comunicação com a Groq?":

```text
messages          user      -> "como o projeto faz a comunicação com a Groq?"
                  assistant -> "[tool_calls] search_project_knowledge"
                  tool      -> {"consulta": "...", "resultados": [...]}
                  assistant -> "O projeto se comunica com a Groq usando..."

tool_executions   search_project_knowledge | 42 ms | sucesso

llm_calls         call 0 -> entrada 1075, saída 150, finish_reason tool_calls
                  call 1 -> entrada 2069, saída 285, finish_reason stop
```

---

## 15. Logging

O projeto não tem arquivo de log: **o banco é o log**. Cada pergunta deixa
rastro em quatro tabelas, e é possível reconstruir a execução inteira com SQL.

A gravação é deliberadamente tolerante a falhas — os métodos de persistência
do orquestrador engolem exceções — para que um problema de banco nunca derrube
uma conversa em andamento.

No terminal, o feedback é mínimo e imediato: uma linha por ferramenta
executada, com o tempo gasto, e um rodapé por resposta com latência, número de
chamadas à LLM, ferramentas usadas, tokens e cache.

---

## 16. Métricas

`get_usage_metrics` aceita três escopos: `session` (a execução atual), `all`
(todo o histórico) e `last_n` (as N chamadas mais recentes). Tudo sai de
agregações SQL:

```sql
SELECT COUNT(*), SUM(prompt_tokens), AVG(prompt_tokens),
       MIN(prompt_tokens), MAX(prompt_tokens), ...
FROM llm_calls
WHERE interaction_id IN (SELECT id FROM interactions WHERE session_id = ?)
```

O retorno traz, para tokens de entrada, de saída e totais: total, média,
mínimo e máximo. Para latência: total, média, mínima e máxima. Para cache:
`cached_tokens`, `prompt_tokens` e a taxa de acerto. Para ferramentas: total
de execuções, média por interação, ferramenta mais usada, ranking e falhas.

---

## 17. Cache

A Groq informa quantos tokens de entrada foram atendidos pelo cache de prompt:

```text
usage.prompt_tokens_details.cached_tokens
```

A taxa é calculada como:

```text
cache_hit_rate = cached_tokens / prompt_tokens * 100
```

Não existe cache de saída: `completion_tokens` sempre é cobrado. Para
aproveitar o cache, o projeto mantém **estável o prefixo do histórico**: o
prompt de sistema é fixo e as definições das seis ferramentas são geradas
sempre na mesma ordem (`ToolRegistry` preserva a ordem de registro). Numa
conversa com várias rodadas de ferramenta o efeito aparece: uma execução real
registrou `cached_tokens = 256` na segunda chamada da mesma interação.

---

## 18. Suíte de testes

Quinze testes offline (T01 a T15) e um de integração (T90). Os offline não
gastam tokens e criam bancos temporários em `java.io.tmpdir` com nome baseado
em `java.util.UUID`, apagados no `tearDown`: o banco de produção nunca é
tocado.

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

O executor aceita `all`, identificadores (`T08,T09`) ou palavra-chave
(`fuzzy`, `banco`, `tools`), e devolve resultado estruturado: total,
passaram, falharam, tempo e o detalhe de cada falha.

---

## 19. Docker

Build em dois estágios:

```text
Estágio 1 (maven:3.9-eclipse-temurin-11)
    lê o pom.xml
    baixa jython-standalone, sqlite-jdbc e commons-text
    coloca os JARs em /opt/lib

Estágio 2 (eclipse-temurin:11-jre)
    copia /opt/lib do estágio anterior
    copia o código Python
    cria o usuário chat (sem privilégios)
    declara o volume /app/data
```

A execução mudou de `java -jar` para **classpath**, porque o Jython precisa
enxergar o driver JDBC e o Commons Text:

```text
java -Dfile.encoding=UTF-8 \
     -Dpython.console.encoding=UTF-8 \
     -Dpython.cachedir=/tmp/jython-cache \
     -cp "/opt/lib/*:/app" \
     org.python.util.jython main.py
```

O curinga do `-cp` é expandido pela própria JVM. `ENTRYPOINT` fixa o
interpretador e `CMD` escolhe o script (`main.py` por padrão).

---

## 20. Configuração por `.env`

O programa **não lê o `.env`**. Quem lê é o Docker, que injeta as variáveis no
container; dentro dele, `java.lang.System.getenv()` as recupera.

```text
.env --(docker run --env-file)--> container --> System.getenv() --> Jython
```

| Variável | Padrão | Para que serve |
| --- | --- | --- |
| `GROQ_API_KEY` | *(obrigatória)* | Autenticação na Groq |
| `GROQ_MODEL` | `openai/gpt-oss-120b` | Modelo usado |
| `GROQ_API_URL` | endpoint de chat completions | Endereço da API |
| `GROQ_TEMPERATURE` | `1.0` | Criatividade (1.0 é o recomendado para o gpt-oss) |
| `GROQ_REASONING_EFFORT` | `medium` | Quanto o modelo raciocina: low, medium ou high |
| `AGENT_CONTEXT_TURNS` | `4` | Perguntas anteriores mantidas no contexto |
| `GROQ_MAX_TOKENS` | `1500` | Limite de tokens por resposta |
| `GROQ_MAX_RETRIES` | `3` | Repetições em HTTP 429/5xx |
| `AGENT_MAX_ITERATIONS` | `5` | Rodadas de ferramenta por pergunta |
| `DATABASE_PATH` | `<projeto>/data/jython_ai_chat.db` | Arquivo SQLite |
| `KNOWLEDGE_DIR` | `<projeto>/knowledge` | Base de conhecimento |
| `KNOWLEDGE_TOP_K` | `3` | Trechos por consulta |
| `KNOWLEDGE_MIN_SCORE` | `0.35` | Score mínimo de relevância |
| `HISTORY_SEARCH_LIMIT` | `5` | Conversas por busca no histórico |

---

## 21. Segurança

- A chave só existe no `.env` local e nas variáveis de ambiente do container.
  Está no `.gitignore` e no `.dockerignore`, e o `Dockerfile` copia arquivos
  explícitos em vez de `COPY . .`.
- No terminal, a chave aparece sempre mascarada (`gsk_********KdLl`).
- O modelo não executa código arbitrário: só os seis nomes da lista branca,
  com argumentos validados contra o schema.
- Todo SQL usa `PreparedStatement` parametrizado.
- O container roda com usuário sem privilégios (`chat`, uid 10001).
- Resultados de ferramenta são truncados antes de voltar ao modelo, limitando
  o consumo de tokens.

---

## 22. Limitações

- A busca é lexical, não semântica: sinônimos sem raiz comum ("busca
  aproximada" contra "fuzzy") não são encontrados.
- A janela de contexto cresce durante a sessão; não há sumarização automática
  do histórico antigo.
- O free tier da Groq limita tokens por minuto; o agente reduz o impacto com
  repetição automática, mas conversas longas podem esperar alguns segundos.
- O `/clear` limpa apenas o contexto em memória; o histórico gravado
  permanece no banco (é o que permite `search_chat_history`).
- Jython implementa Python 2.7, então não há f-strings, `pathlib` nem
  bibliotecas que exijam extensões C.

---

## 23. Possíveis evoluções

- Sumarizar automaticamente interações antigas para conter o crescimento do
  contexto.
- Índice invertido para a busca lexical, evitando varrer todos os trechos.
- Ferramenta de escrita (criar ou atualizar documentos da base), com
  confirmação explícita do usuário.
- Exportar as métricas em CSV ou JSON para análise fora do terminal.
- Streaming da resposta, para o texto aparecer conforme é gerado.
- Suporte a mais de um modelo, comparando custo e latência entre eles.
