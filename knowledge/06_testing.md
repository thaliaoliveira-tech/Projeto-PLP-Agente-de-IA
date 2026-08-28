# Testes automatizados

## Organização

A suíte usa o módulo unittest da biblioteca padrão do Python, executado pelo
Jython. O arquivo tests/registry.py associa um identificador legível a cada
método de teste, o que permite ao agente listar e executar testes
selecionados pelo nome ou pelo identificador.

## Testes disponíveis

T01 verifica a configuração padrão do modelo. T02 verifica que o histórico da
conversa usa java.util.ArrayList. T03 verifica a adição de mensagens de
usuário e de assistente. T04 verifica que a limpeza do contexto preserva o
prompt de sistema. T05 verifica que o payload enviado à Groq inclui as
ferramentas. T06 verifica que o parser reconhece tool_calls. T07 verifica que
o registro encontra uma ferramenta válida e rejeita uma inválida.

T08 verifica a busca fuzzy com correspondência exata. T09 verifica a busca
fuzzy com erro de digitação. T10 verifica que a busca na base de conhecimento
respeita o limite top_k. T11 verifica que o banco cria todas as tabelas. T12
verifica que uma interação completa é gravada corretamente. T13 verifica o
cálculo de tokens, cache e latência. T14 verifica a busca fuzzy no histórico
de conversas.

## Testes offline

Os quinze testes são offline e não gastam tokens da Groq. Eles usam bancos
temporários criados em arquivos com nome aleatório, apagados ao final, de modo
que o banco de produção nunca é tocado.

## Teste de integração

O teste T90 é o único que chama a Groq de verdade. Ele não entra na execução
padrão e só roda quando pedido explicitamente, para não consumir a quota da
API à toa.

## Janela de contexto

O teste T15 verifica a janela de contexto deslizante: o agente mantém apenas
as últimas rodadas de conversa no contexto enviado à LLM, controladas pela
variável AGENT_CONTEXT_TURNS. O corte é sempre feito antes de uma mensagem do
usuário, para nunca separar um pedido de ferramenta do resultado
correspondente, porque a API rejeita uma mensagem de papel tool sem o tool
call que a originou.
