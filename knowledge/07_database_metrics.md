# Banco de dados e métricas

## SQLite por JDBC

O projeto não usa o módulo sqlite3 do CPython. A persistência é feita com
java.sql, o driver JDBC do SQLite da Xerial e a URL de conexão
jdbc:sqlite: seguida do caminho do arquivo. A conexão é aberta com
DriverManager.getConnection, as instruções são preparadas com
prepareStatement e os resultados vêm em um ResultSet, exatamente como em uma
aplicação Java.

## Tabelas

São cinco tabelas. A tabela sessions guarda cada execução do programa, com
início, fim, modelo e versões de Jython e Java. A tabela interactions guarda
cada pergunta completa do usuário, com tempo total e situação. A tabela
messages guarda cada mensagem trocada, com papel system, user, assistant ou
tool. A tabela llm_calls guarda cada chamada ao modelo, porque uma única
pergunta pode gerar duas ou três chamadas por causa das ferramentas. A tabela
tool_executions guarda cada execução de ferramenta, com argumentos, resultado,
duração e sucesso ou erro.

## O que fica registrado em llm_calls

Cada chamada grava o índice dentro da interação, o modelo, os tokens de
entrada, os tokens de saída, o total, os tokens vindos do cache, os tempos
informados pela Groq para fila, prompt e conclusão, o tempo medido localmente
e o motivo de encerramento.

## Métricas

As consultas de métricas usam funções de agregação SQL: COUNT, SUM, AVG, MIN e
MAX. São apuradas as estatísticas de tokens de entrada, tokens de saída,
tokens totais e latência, além da taxa de acerto do cache, calculada como a
soma dos tokens em cache dividida pela soma dos tokens de entrada.

Também há estatísticas de ferramentas: total de execuções, média por
interação, ferramenta mais usada e quantidade de falhas.

## Persistência entre execuções

O banco fica em um volume Docker montado em /app/data. Assim o container pode
ser destruído e recriado sem perder o histórico das conversas nem as métricas
acumuladas.

## Colunas de auditoria de rede

A tabela llm_calls também grava quantas requisições HTTP foram necessárias para
cada chamada, na coluna http_attempts, e quanto tempo o cliente ficou esperando
por causa de erros temporários, na coluna retry_wait_ms. A tabela interactions
tem uma coluna error que guarda a mensagem de erro quando uma pergunta não pôde
ser respondida. Bancos criados por versões anteriores recebem essas colunas
automaticamente na abertura da conexão, por uma migração que usa PRAGMA
table_info para descobrir o que está faltando.
