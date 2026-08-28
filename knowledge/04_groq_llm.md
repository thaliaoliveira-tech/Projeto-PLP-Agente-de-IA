# Groq, LLM e tool calling

## Modelo e endpoint

O projeto usa o modelo openai/gpt-oss-120b servido pela Groq, através da Chat
Completions API, no endereço https://api.groq.com/openai/v1/chat/completions.
A requisição é um POST com cabeçalho Authorization contendo Bearer e a chave
da API, e Content-Type application/json.

## Como a requisição é montada

O corpo enviado contém o modelo, a lista de mensagens, a temperatura, o limite
de tokens de resposta e, quando o agente está ativo, a lista de ferramentas
disponíveis com seus schemas JSON e o campo tool_choice igual a auto.

Toda a comunicação é feita por classes Java: java.net.URL cria o endereço,
HttpURLConnection abre a conexão HTTPS e configura o método POST,
OutputStreamWriter escreve o JSON no socket e InputStreamReader com
BufferedReader leem a resposta.

## Tool calling

Quando o modelo decide usar uma ferramenta, ele não devolve texto: devolve o
campo tool_calls, com identificador, nome da função e argumentos em JSON. A
aplicação executa a função localmente, acrescenta ao histórico uma mensagem de
papel tool com o identificador correspondente e chama o modelo novamente. Esse
ciclo se repete até o modelo devolver conteúdo textual, respeitando o limite
de iterações.

## Prompt caching

A Groq informa o consumo de tokens no campo usage, com prompt_tokens,
completion_tokens e total_tokens, além de prompt_tokens_details.cached_tokens,
que indica quantos tokens de entrada foram atendidos pelo cache de prompt.

A taxa de acerto do cache é calculada dividindo cached_tokens por
prompt_tokens. O cache só existe para tokens de entrada; não há cache de
saída. Para aproveitá-lo, o prompt de sistema e as definições das ferramentas
são mantidos estáveis entre as requisições, sempre no mesmo prefixo do
histórico.

## Métricas de tempo

A resposta da Groq também traz tempos internos no campo usage: queue_time,
prompt_time, completion_time e total_time. O projeto grava esses valores junto
com o tempo medido localmente por System.currentTimeMillis.

## Erros temporários e repetição automática

Quando o limite de tokens por minuto é atingido, a Groq responde HTTP 429 e
informa na própria mensagem quanto tempo falta para tentar de novo. O cliente
lê esse tempo, avisa no terminal e repete a chamada usando java.lang.Thread e
seu método sleep. O mesmo vale para erros HTTP 5xx. A variável de ambiente
GROQ_MAX_RETRIES define quantas repetições são aceitas antes de o erro chegar
ao usuário; o padrão é duas.

## Esforço de raciocínio

O gpt-oss-120b é um modelo de raciocínio: ele sempre pensa antes de responder,
e esse pensamento é cobrado como tokens de saída. O parâmetro reasoning_effort
define quanto ele pensa e aceita os valores low, medium e high. O projeto usa
medium por padrão, configurável pela variável GROQ_REASONING_EFFORT. O valor
low economiza tokens de saída, mas degrada a qualidade quando o modelo precisa
resumir o resultado de uma ferramenta.

## Janela de contexto

O agente não reenvia a conversa inteira a cada pergunta. A variável
AGENT_CONTEXT_TURNS define quantas perguntas anteriores continuam no contexto,
quatro por padrão. Sem esse limite, cada pergunta ficaria mais cara que a
anterior, porque o histórico cresce, e o limite de tokens por minuto do plano
gratuito seria atingido rapidamente. O corte é sempre feito antes de uma
mensagem do usuário, para nunca separar um pedido de ferramenta do resultado
correspondente.

## O campo reasoning no histórico

O gpt-oss devolve o raciocínio em um campo separado chamado reasoning, além do
texto final em content. Esse campo precisa ser reenviado ao modelo dentro da
mensagem de papel assistant que pediu ferramentas. Sem isso, o modelo perde a
própria linha de raciocínio e, depois de algumas perguntas parecidas, começa a
degenerar em repetição, produzindo respostas com reticências e traços sem
sentido. Esse problema foi reproduzido e corrigido no projeto, e o diagnóstico
completo está no documento LLM_AND_TOOLS.md.

Outro detalhe da mesma família: a temperatura recomendada para o gpt-oss é 1.0.
Temperaturas baixas, como 0.4, aumentam a pressão de repetição em modelos de
raciocínio e agravam o mesmo colapso.
