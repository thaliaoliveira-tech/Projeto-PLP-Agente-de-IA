# LLM_AND_TOOLS — Como a IA funciona neste projeto

Documento dedicado à camada de inteligência artificial. A arquitetura geral
está em [PROJECT_GUIDE.md](PROJECT_GUIDE.md); aqui o assunto é só o modelo, o
tool calling e o laço agentivo.

---

## Perguntas que acionam Caelum Stella

| Pergunta do usuário | Tool esperada |
| --- | --- |
| O CPF 529.982.247-25 é válido? | `stella_validate_document` |
| Formate o CPF 52998224725. | `stella_transform_document` |
| Gere um CPF válido para teste. | `stella_generate_document` |
| Escreva 123 por extenso. | `stella_number_to_words` |
| Quais capabilities a Stella possui? | `stella_capabilities` |
| Valide estes CPFs em lote: ... | `stella_validate_batch` |

Inscrição estadual usa a mesma tool de validação com `document_type` igual a
`inscricao_estadual` e `uf` obrigatória. Para não transmitir um documento à
Groq, o usuário deve usar o comando local `/stella`.

## Caelum Stella

As tools Stella expõem capabilities, não classes Java; documentos são
redigidos antes da auditoria SQLite e a LLM deve usar a tool de validação.

## 1. O modelo: openai/gpt-oss-120b

O agente usa o `openai/gpt-oss-120b` servido pela **Groq**. É um modelo aberto,
de grande porte, com suporte a *function calling* — condição necessária para
tudo o que este projeto faz.

A comunicação é a Chat Completions API:

```text
POST https://api.groq.com/openai/v1/chat/completions
Authorization: Bearer $GROQ_API_KEY
Content-Type: application/json
```

Toda a chamada é montada por classes Java (`java.net.URL`,
`HttpURLConnection`, `java.io.OutputStreamWriter`), sem nenhuma biblioteca
Python de rede.

---

## 2. O system prompt

O prompt de sistema é fixo e vive em `config.DEFAULT_SYSTEM_PROMPT`. Ele faz
três coisas.

Primeiro, dá identidade e contexto ao modelo:

```text
Você é o assistente do Jython AI Agent, um projeto acadêmico escrito em
Python e executado pelo Jython sobre a JVM, que usa APIs Java para rede,
streams, coleções e banco de dados.
```

Segundo, define quando cada ferramenta deve ser usada:

```text
1. Pergunta sobre este projeto -> chame search_project_knowledge antes de
   responder.
2. Listar testes -> list_project_tests.
3. Executar testes -> run_project_tests.
4. Conversas anteriores -> search_chat_history ou get_recent_interactions.
5. Tokens, cache, latência ou uso -> get_usage_metrics.
6. NUNCA invente resultados de ferramentas nem números de métricas.
7. Depois de executar uma ferramenta, transforme o resultado em resposta
   clara; não devolva JSON cru ao usuário.
```

Terceiro, fixa o estilo: texto puro, em português do Brasil, sem Markdown,
porque a saída é um terminal.

O prompt ser **fixo** não é detalhe: é o que permite que ele participe do
prompt caching da Groq.

---

## 3. Tool schemas

Cada ferramenta é declarada em JSON Schema e enviada no corpo da requisição:

```json
{
  "type": "function",
  "function": {
    "name": "search_project_knowledge",
    "description": "Pesquisa na documentação local do projeto Jython AI Agent. Use SEMPRE que a pergunta for sobre este projeto...",
    "parameters": {
      "type": "object",
      "properties": {
        "query": { "type": "string", "description": "Termos de busca..." },
        "limit": { "type": "integer", "description": "1 a 8. Padrão: 3." }
      },
      "required": ["query"]
    }
  }
}
```

A `description` é parte do prompt: é lendo esse texto que o modelo decide se a
ferramenta serve para a pergunta. Por isso as descrições dizem **quando usar**,
não apenas o que a função faz.

As seis ferramentas são sempre enviadas na mesma ordem, junto de
`"tool_choice": "auto"` — o modelo decide se usa alguma.

---

## 4. As seis ferramentas

| Ferramenta | Parâmetros | O que devolve |
| --- | --- | --- |
| `search_project_knowledge` | `query`, `limit` | Trechos da documentação local com score de similaridade |
| `list_project_tests` | `only` | Catálogo de testes (id, nome, descrição, tipo) |
| `run_project_tests` | `target` | Total, passaram, falharam, tempo e detalhe das falhas |
| `search_chat_history` | `query`, `limit` | Conversas antigas relevantes, com score |
| `get_recent_interactions` | `limit`, `scope` | Últimas interações em ordem cronológica inversa |
| `get_usage_metrics` | `scope`, `limit` | Tokens, cache, latência e uso de ferramentas |

Todas são **determinísticas**: nenhuma delas chama outro modelo. O único
componente probabilístico do sistema é o orquestrador.

---

## 5. O agentic loop

```text
     pergunta do usuário
             │
             ▼
   ┌──────────────────────┐
   │ envia histórico +    │◄────────────────────────────┐
   │ tool schemas à Groq  │                             │
   └──────────┬───────────┘                             │
              │                                         │
        a resposta tem                                  │
        tool_calls?                                     │
         │        │                                     │
      não│        │sim                                  │
         │        ▼                                     │
         │  valida na lista branca                      │
         │        │                                     │
         │  executa a ferramenta localmente             │
         │        │                                     │
         │  grava em tool_executions                    │
         │        │                                     │
         │  insere mensagem role="tool"                 │
         │        │                                     │
         │        └─────────────────────────────────────┘
         ▼                              (até AGENT_MAX_ITERATIONS)
   resposta final ao usuário
```

Uma pergunta simples gasta **1 chamada** à LLM. Uma pergunta que usa
ferramenta gasta **2**: a primeira devolve `tool_calls`, a segunda devolve o
texto final. Se o modelo encadear ferramentas, o número cresce — e é
exatamente isso que o limite de iterações contém.

---

## 6. Como uma tool call chega e volta

O modelo devolve, em vez de texto:

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
          "arguments": "{\"query\": \"docker configuração jython\"}"
        }
      }]
    }
  }]
}
```

O `groq_client` converte isso em objetos `ToolCall`. O orquestrador executa a
ferramenta e devolve o resultado ao modelo como uma mensagem de papel `tool`,
amarrada pelo mesmo identificador:

```json
{
  "role": "tool",
  "tool_call_id": "call_abc123",
  "name": "search_project_knowledge",
  "content": "{\"consulta\": \"docker configuração jython\", \"encontrados\": 3, \"resultados\": [...]}"
}
```

Na rodada seguinte, o modelo já tem o resultado no histórico e escreve a
resposta final.

---

## 7. Recuperação de conhecimento

`search_project_knowledge` é um **RAG lexical local**: sem embeddings, sem
banco vetorial, sem serviço externo.

```text
pergunta
   ↓ normalização (java.text.Normalizer, minúsculas, stopwords)
   ↓ ranking fuzzy (Apache Commons Text) sobre 25 trechos
   ↓ top_k = 3, score mínimo 0.35
3 trechos de até 1.000 caracteres
   ↓
modelo escreve a resposta
```

Em vez de mandar o README e o código inteiros a cada pergunta (dezenas de
milhares de tokens), vão a pergunta e três trechos pequenos. É a diferença
entre uma requisição de ~1.000 tokens e uma de ~20.000.

O resultado devolvido ao modelo mostra o score de cada trecho, o que o ajuda a
calibrar a confiança — e quando nada passa do score mínimo, a ferramenta
devolve explicitamente uma observação dizendo que a documentação local não
cobre o assunto.

---

## 8. Tokens e cache

Cada resposta da Groq traz:

```text
usage.prompt_tokens                            tokens de entrada
usage.completion_tokens                        tokens de saída
usage.total_tokens                             soma
usage.prompt_tokens_details.cached_tokens      entrada atendida pelo cache
usage.queue_time / prompt_time / completion_time / total_time
```

Tudo isso é gravado em `llm_calls`, junto do tempo medido localmente por
`System.currentTimeMillis()`. A taxa de cache é:

```text
cache_hit_rate = cached_tokens / prompt_tokens * 100
```

Só existe cache de **entrada**. Para aproveitá-lo, o prefixo do histórico
precisa ser idêntico entre requisições — por isso o system prompt é fixo e os
schemas das ferramentas são gerados sempre na mesma ordem. Numa interação real
com duas rodadas, a segunda chamada registrou 256 tokens vindos do cache.

---

## 9. Limite de iterações

`AGENT_MAX_ITERATIONS` (5 por padrão) limita quantas rodadas de ferramenta uma
única pergunta pode disparar. Ao estourar:

```text
[ERRO] Limite de execução de ferramentas atingido (5 iterações).
       Reformule a pergunta ou aumente AGENT_MAX_ITERATIONS.
```

O contexto volta ao estado anterior à pergunta (`rollback_to`), para que a
conversa continue consistente, e a interação é fechada no banco com status
`limit`.

---

## 10. Tratamento de alucinação

Quatro camadas reduzem invenção de fatos:

1. **Regra explícita no system prompt**: para perguntas sobre o projeto, o
   modelo deve consultar `search_project_knowledge` antes de responder, e
   nunca inventar resultados de ferramenta ou números de métrica.
2. **Dados reais no contexto**: métricas, resultados de teste e conversas
   antigas chegam ao modelo como mensagens `tool` com valores verdadeiros,
   vindos de SQL e de `unittest` — não são estimativas.
3. **Score visível**: cada trecho recuperado vem com seu score; nada é
   apresentado como certeza absoluta.
4. **Auditoria**: tudo o que a ferramenta devolveu fica gravado em
   `tool_executions`, então é possível conferir depois se a resposta bate com
   o que a ferramenta realmente disse.

O que **não** é resolvido: se a pergunta for sobre um assunto fora da base de
conhecimento, o modelo ainda pode responder com conhecimento geral. Nesse caso
a ferramenta devolve `encontrados: 0` e uma observação pedindo cautela.

---

## 11. Erros temporários

O free tier da Groq limita tokens por minuto. Quando o limite é atingido, a
API responde HTTP 429 dizendo quanto esperar:

```text
Rate limit reached ... Please try again in 5.1525s
```

O cliente lê esse tempo, avisa no terminal e repete a chamada usando
`java.lang.Thread.sleep`:

```text
[a Groq respondeu HTTP 429; aguardando 5.6s antes da tentativa 2]
```

O mesmo vale para HTTP 5xx. `GROQ_MAX_RETRIES` controla quantas repetições são
aceitas antes de a mensagem de erro chegar ao usuário.

---

## 12. Custo de uma conversa

Números observados em execuções reais deste projeto:

| Tipo de pergunta | Chamadas à LLM | Tokens totais | Tempo |
| --- | --- | --- | --- |
| Conversa comum, sem ferramenta | 1 | ~700 | ~0,8 s |
| Consulta ao conhecimento | 2 | ~2.800 | ~5,5 s |
| Execução de testes | 2 | ~1.400 | ~1,9 s |
| Consulta de métricas | 2 | ~1.800 | ~1,1 s |
| Busca no histórico | 2 | ~1.650 | ~1,8 s |

O peso fixo de cada requisição é o system prompt somado aos seis schemas de
ferramenta — algo em torno de 800 tokens, justamente a parte que o prompt
caching consegue reaproveitar.

---

## 13. O raciocínio precisa voltar ao histórico

Esta seção documenta um bug real encontrado e corrigido durante o
desenvolvimento — vale mais que qualquer teoria.

**Sintoma.** Ao pedir vários testes em sequência (`execute o teste T02`, depois
`agora o T03`, depois `agora o T15`), a primeira resposta vinha correta, a
segunda vinha com lixo no começo e a terceira degenerava por completo:

```text
Teste ****?

---

---
... ... ...
Desculpe desculpe...
```

**O que não era.** Três hipóteses foram testadas e descartadas com medição:

| Hipótese | Resultado |
| --- | --- |
| Resíduo de tool calls antigos no contexto | Colapsar o rastro não resolveu |
| `frequency_penalty` / `presence_penalty` contra repetição | **Piorou** — penalidades atrapalham modelos de raciocínio |
| `reasoning_effort=low` para economizar tokens | Piorou: com esforço baixo o modelo se atrapalha ao resumir ferramentas |

**O que era.** Duas causas somadas:

1. O `gpt-oss-120b` devolve o raciocínio em um campo separado, `reasoning`. Ao
   reenviar o histórico **sem** esse campo na mensagem que pediu a ferramenta,
   o modelo perde a própria linha de raciocínio e, depois de algumas rodadas
   parecidas, colapsa em repetição.
2. `temperature=0.4` é baixa demais para um modelo de raciocínio. O valor
   recomendado para o gpt-oss é **1.0**; temperaturas baixas aumentam a
   pressão de repetição quando o contexto já tem respostas quase idênticas.

**A correção.** `GroqReply` passou a guardar `reasoning`, e
`ChatSession.add_assistant_tool_calls()` o reenvia junto do `tool_calls`:

```python
{
  "role": "assistant",
  "content": null,
  "reasoning": "O usuário quer rodar o T03; vou chamar run_project_tests.",
  "tool_calls": [ { "id": "call_...", "function": { "..." : "..." } } ]
}
```

O `reasoning` só volta na mensagem **intermediária** (a que pede ferramentas).
Na resposta final ele é descartado, porque medimos que ali não faz diferença e
custaria tokens à toa.

**Resultado medido**, no mesmo roteiro de quatro perguntas seguidas:

| | Antes | Depois |
| --- | --- | --- |
| Respostas limpas | 1 de 4 | **4 de 4** |
| Tokens por interação | ~4.400 | **~1.650** |
| Tempo por resposta | 21 s a 34 s | **1,1 s a 1,4 s** |
| HTTP 429 | em quase toda pergunta | **nenhum** |
| Cache aproveitado | esporádico | 1.024 tokens em todas |

A lição vale para qualquer agente com modelo de raciocínio: **o histórico
reenviado precisa ser exatamente o que o modelo produziu**, incluindo o que ele
"pensou", e não apenas o texto que o usuário viu.
