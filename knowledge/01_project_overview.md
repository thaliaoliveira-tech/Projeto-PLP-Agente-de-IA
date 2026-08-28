# Visão geral do projeto

## O que é o Jython AI Agent

O Jython AI Agent é um assistente técnico de terminal escrito em Python e
executado pelo Jython sobre a JVM. Ele conversa com o modelo
`openai/gpt-oss-120b` hospedado na Groq e, além de responder em linguagem
natural, é capaz de executar ferramentas locais para consultar a própria
documentação, rodar a suíte de testes, pesquisar conversas antigas e apurar
métricas de uso.

O projeto foi desenvolvido para a disciplina Paradigmas de Linguagens de
Programação e tem como objetivo demonstrar, na prática, a interoperabilidade
entre Python e Java quando as duas linguagens compartilham a mesma plataforma
de execução.

## O que o agente faz

O usuário digita uma pergunta no terminal. O modelo decide sozinho se consegue
responder direto ou se precisa de uma ferramenta. Quando precisa, ele devolve
uma chamada de função, a aplicação executa a função localmente e devolve o
resultado ao modelo, que então escreve a resposta final para o humano.

Perguntas típicas que disparam ferramentas:

- "como o projeto conversa com a Groq?" consulta a base de conhecimento
- "quais testes existem?" lista a suíte de testes
- "rode os testes de fuzzy" executa os testes selecionados
- "já falamos sobre busca aproximada?" pesquisa o histórico no banco
- "quantos tokens já usamos?" apura as métricas gravadas no SQLite

## Princípios do projeto

Nada de biblioteca Python que esconda a plataforma Java. Não são usados
requests, urllib, httplib, sqlite3 do CPython, groq-python nem openai-python.
Rede, streams, coleções, banco de dados e similaridade textual são resolvidos
com classes e bibliotecas Java chamadas diretamente do código Python.

Também não há embeddings nem banco vetorial: a recuperação de contexto é
lexical, feita com Apache Commons Text.

## Números do projeto

São 6 ferramentas expostas ao modelo, 8 documentos na base de conhecimento,
5 tabelas no banco de dados e 15 testes automatizados offline, mais um teste
de integração opcional que fala com a Groq de verdade.
