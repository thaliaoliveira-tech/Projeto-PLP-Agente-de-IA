# ---------------------------------------------------------------------------
# Jython AI Agent -- imagem de execução (build em dois estágios)
#
#   Estágio 1 (deps)    : Maven resolve os JARs declarados no pom.xml
#   Estágio 2 (runtime) : Java 11 + JARs + código Python do projeto
#
# JARs usados no classpath:
#   jython-standalone -> interpretador Python sobre a JVM
#   sqlite-jdbc       -> driver JDBC do SQLite (java.sql)
#   commons-text      -> similaridade textual (busca fuzzy)
#   caelum-stella-core -> validação e formatação de documentos brasileiros
#
#   docker build -t jython-ai-agent .
#   docker volume create jython-ai-data
#   docker run --rm -it --env-file .env -v jython-ai-data:/app/data jython-ai-agent
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Estágio 1 -- download das dependências Java
# ---------------------------------------------------------------------------
FROM maven:3.9-eclipse-temurin-11 AS deps

WORKDIR /build
COPY pom.xml ./

RUN mvn -B -q dependency:copy-dependencies \
    -DoutputDirectory=/opt/lib \
    -DincludeScope=runtime \
    && ls -1 /opt/lib

# ---------------------------------------------------------------------------
# Estágio 2 -- runtime
# ---------------------------------------------------------------------------
FROM eclipse-temurin:11-jre

LABEL org.opencontainers.image.title="Jython AI Agent"
LABEL org.opencontainers.image.description="Assistente tecnico agentivo em Python/Jython sobre a JVM, com tool calling, SQLite via JDBC e busca fuzzy com Apache Commons Text"

# JARs vindos do estágio anterior (sem Maven na imagem final).
COPY --from=deps /opt/lib /opt/lib

# Usuário sem privilégios.
RUN useradd --create-home --uid 10001 --shell /usr/sbin/nologin chat

WORKDIR /app

# ---------------------------------------------------------------------------
# Código do projeto.
#
# O arquivo .env NUNCA entra na imagem: a chave da API é injetada somente na
# execução, via docker run --env-file .env
# ---------------------------------------------------------------------------
COPY --chown=chat:chat *.py ./
COPY --chown=chat:chat knowledge/ ./knowledge/
COPY --chown=chat:chat search/ ./search/
COPY --chown=chat:chat database/ ./database/
COPY --chown=chat:chat tools/ ./tools/
COPY --chown=chat:chat stella/ ./stella/
COPY --chown=chat:chat tests/ ./tests/
COPY --chown=chat:chat docs/ ./docs/
COPY --chown=chat:chat README.md pom.xml ./

# Diretório do banco SQLite -- montado como volume para sobreviver ao container.
RUN mkdir -p /app/data && chown chat:chat /app/data
VOLUME ["/app/data"]

USER chat

# ---------------------------------------------------------------------------
# Execução
#
# O Jython é iniciado por CLASSPATH (e não por "java -jar"), para que enxergue
# o driver JDBC do SQLite e o Apache Commons Text. O curinga do -cp é expandido
# pela própria JVM.
#
#   docker run --rm -it --env-file .env -v jython-ai-data:/app/data jython-ai-agent
# ---------------------------------------------------------------------------
ENTRYPOINT ["java", \
    "-Dfile.encoding=UTF-8", \
    "-Dpython.console.encoding=UTF-8", \
    "-Dpython.cachedir=/tmp/jython-cache", \
    "-cp", "/opt/lib/*:/app", \
    "org.python.util.jython"]

CMD ["main.py"]
