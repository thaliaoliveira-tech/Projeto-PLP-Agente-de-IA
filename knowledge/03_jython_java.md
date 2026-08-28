# Jython e a integração com Java

## O que é Jython

Jython é uma implementação da linguagem Python que executa sobre a Java
Virtual Machine. O código Python é compilado para bytecode Java e roda na JVM.
Diferentemente do CPython, escrito em C, o Jython permite importar e usar
classes e bibliotecas Java diretamente dentro de programas Python, como se
fossem módulos comuns.

A versão usada no projeto é a 2.7.4, que corresponde à linguagem Python 2.7 e
tem suporte a Java 8 e Java 11.

## CPython comparado ao Jython

CPython é escrito em C, executa em seu próprio interpretador, acompanha a
versão 3.x da linguagem e usa extensões nativas como NumPy, mas não enxerga o
ecossistema Java. Jython é escrito em Java, executa na JVM, implementa a
versão 2.7 da linguagem, não usa extensões C e enxerga todo o ecossistema
Java. Neste projeto isso é a diferença que importa.

## Classes Java usadas

O projeto usa java.net.URL e java.net.HttpURLConnection para a requisição
HTTPS. Usa java.io.OutputStreamWriter para enviar o JSON e
java.io.InputStreamReader com java.io.BufferedReader para ler a resposta e a
entrada do teclado. Usa java.io.PrintWriter para escrever no terminal em
UTF-8. Usa java.lang.System para variáveis de ambiente, propriedades da JVM e
medição de tempo, e java.lang.StringBuilder para montar a resposta.

Usa java.util.ArrayList e java.util.LinkedHashMap para o histórico da
conversa, java.text.Normalizer para remover acentos, java.sql.DriverManager
com JDBC para o banco de dados e as classes JaroWinklerSimilarity e
LevenshteinDistance do Apache Commons Text para similaridade textual.

## Conversão automática de tipos

O Jython converte os tipos das duas linguagens automaticamente. Uma string
Python vira java.lang.String, um booleano Python vira boolean, None vira null
e um java.lang.Integer volta como int. Um laço for de Python itera sobre um
java.util.ArrayList sem nenhuma adaptação, e uma exceção lançada por código
Java é capturada por uma cláusula except de Python.

## Detalhe curioso

System.in não pode ser escrito diretamente em Python porque in é palavra
reservada da linguagem. É preciso usar getattr(System, "in"), um bom exemplo
de onde as duas linguagens se encontram.

## Outras APIs Java do projeto

Além das citadas acima, o projeto usa java.text.Normalizer para remover
acentos na forma NFD, java.time.LocalDateTime para registrar a data e a hora
de cada mensagem, java.util.UUID para gerar nomes de bancos temporários nos
testes, java.lang.Thread para esperar entre tentativas de requisição e
java.lang.Class para carregar o driver JDBC do SQLite.
