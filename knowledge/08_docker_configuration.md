# Docker e configuração

## Imagem Docker

A imagem Docker é construída em dois estágios. No primeiro estágio, o Maven lê
o pom.xml e baixa os JARs necessários: o Jython standalone, o driver JDBC do
SQLite e o Apache Commons Text. No segundo estágio, a imagem de runtime traz
apenas o Java 11 do Eclipse Temurin, os JARs baixados e o código da aplicação.

## Como configurar e executar o Docker

Para configurar o Docker, primeiro construa a imagem com docker build -t
jython-ai-agent e o ponto no final. Depois crie o volume de dados com docker
volume create jython-ai-data. Por fim execute o container com docker run,
usando as opções --rm, -it, --env-file .env e -v jython-ai-data:/app/data.

A configuração do Jython no container acontece pelo classpath: o container não
roda java -jar, e sim java -cp com o diretório de bibliotecas e o diretório da
aplicação, chamando a classe org.python.util.jython seguida do script Python.
Esse detalhe da configuração é o que faz o Jython enxergar o driver JDBC do
SQLite e o Apache Commons Text.

O container também define as propriedades de sistema file.encoding e
python.console.encoding como UTF-8 e um diretório de cache gravável para o
Jython.

## Variáveis de ambiente

A configuração da aplicação é feita por variáveis de ambiente, injetadas pelo
Docker com --env-file. As principais são GROQ_API_KEY, GROQ_MODEL,
GROQ_TEMPERATURE, GROQ_MAX_TOKENS, AGENT_MAX_ITERATIONS, DATABASE_PATH,
KNOWLEDGE_DIR, KNOWLEDGE_TOP_K, KNOWLEDGE_MIN_SCORE e HISTORY_SEARCH_LIMIT.

Todas são lidas por java.lang.System.getenv. O arquivo .env nunca entra na
imagem: ele está no .dockerignore e no .gitignore, e a chave só existe dentro
do container em tempo de execução.

## Volume de dados

O volume jython-ai-data é montado em /app/data e guarda o arquivo
jython_ai_chat.db. Sem esse volume, o histórico seria perdido quando o
container fosse removido pela opção --rm.

## Usuário e permissões

O container roda com um usuário sem privilégios chamado chat, dono do
diretório da aplicação e do diretório de dados.
