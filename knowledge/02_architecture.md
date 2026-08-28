# Arquitetura da aplicação

## Camadas

A aplicação está dividida em camadas bem separadas:

- `main.py` cuida do terminal, do banner e dos comandos.
- `orchestrator.py` implementa o laço agentivo (agentic loop).
- `groq_client.py` fala com a API por meio de classes Java de rede.
- `chat.py` mantém o contexto da conversa em coleções Java.
- `tools/` reúne as ferramentas locais que o modelo pode executar.
- `search/` implementa normalização, chunking e similaridade textual.
- `database/` grava sessões, mensagens, chamadas e métricas.
- `knowledge/` guarda a documentação consultável pelo agente.
- `tests/` contém a suíte automatizada.

## Fluxo de uma mensagem

O caminho completo de uma pergunta é o seguinte. O terminal lê a linha com
BufferedReader. O orquestrador abre uma interação no banco e grava a mensagem
do usuário. O cliente monta o JSON com o histórico e as definições das
ferramentas e faz o POST. O modelo responde com texto final ou com tool_calls.
Havendo tool_calls, cada ferramenta é executada localmente, o resultado é
gravado e devolvido ao modelo como mensagem de papel tool, e o modelo é
chamado novamente. Quando vem conteúdo textual, a resposta é gravada e
impressa no terminal.

## Separação entre orquestrador e ferramentas

O orquestrador nunca executa código arbitrário. Ele só conhece o registro de
ferramentas, que funciona como uma lista branca. Se o modelo pedir uma função
inexistente, o registro devolve um erro controlado em vez de executar
qualquer coisa. Não existe eval, exec, shell nem subprocess dirigido pelo
modelo.

## Limite de iterações

O laço agentivo tem um limite configurável de iterações, cinco por padrão,
definido por AGENT_MAX_ITERATIONS. Ao atingir o limite, a interação é
encerrada com uma mensagem de erro amigável, evitando laços infinitos de
chamadas de ferramenta.
