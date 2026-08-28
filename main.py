# -*- coding: utf-8 -*-
"""
main.py -- Ponto de entrada do Jython AI Agent.

Assistente técnico agentivo de terminal, escrito em Python, executado pelo
Jython sobre a JVM e integrado à API da Groq (modelo openai/gpt-oss-120b).

Este arquivo cuida apenas do terminal e do bootstrap:

    valida a configuração  ->  conecta o banco (JDBC)  ->  carrega a base de
    conhecimento  ->  monta o registro de ferramentas  ->  entrega tudo ao
    orquestrador  ->  laço de leitura do terminal

Até a entrada e a saída passam por classes Java: em vez de ``print`` e
``raw_input``, usamos ``java.io.PrintWriter`` e ``java.io.BufferedReader``,
garantindo UTF-8 correto em qualquer sistema operacional.

APIs Java utilizadas neste módulo:

    java.lang.System           -> System.out, System.err e System.in
    java.io.OutputStreamWriter -> saída de texto em UTF-8
    java.io.PrintWriter        -> escreve no terminal
    java.io.InputStreamReader  -> entrada de texto em UTF-8
    java.io.BufferedReader     -> lê a linha digitada pelo usuário

Execução:

    java -cp "/opt/lib/*:/app" org.python.util.jython main.py
"""
from __future__ import unicode_literals

import re
import sys
import json

from java.lang import System
from java.io import BufferedReader
from java.io import InputStreamReader
from java.io import OutputStreamWriter
from java.io import PrintWriter

import config
import orchestrator as orchestrator_module
from chat import ChatSession
from groq_client import GroqClient
from database.connection import Database, DatabaseError
from database.interaction_repository import InteractionRepository
from database.metrics_repository import MetricsRepository
from tools import build_registry
from tools.registry import ToolContext
from tools.knowledge_tool import KnowledgeBase
from stella.service import StellaService
from stella.errors import StellaError


# ---------------------------------------------------------------------------
# Terminal: entrada e saída construídas sobre java.io.
# "System.in" precisa de getattr() porque "in" é palavra reservada em Python.
# ---------------------------------------------------------------------------
STDOUT = PrintWriter(OutputStreamWriter(System.out, "UTF-8"), True)
STDERR = PrintWriter(OutputStreamWriter(System.err, "UTF-8"), True)
STDIN = BufferedReader(InputStreamReader(getattr(System, "in"), "UTF-8"))

LINE = "=" * 50

TOOL_LABELS = {
    "search_project_knowledge": "consultando o conhecimento do projeto",
    "list_project_tests": "listando os testes do projeto",
    "run_project_tests": "executando os testes",
    "search_chat_history": "pesquisando o histórico de conversas",
    "get_recent_interactions": "recuperando as conversas recentes",
    "get_usage_metrics": "consultando as métricas de uso",
    "stella_validate_document": "executando tool de validação Stella",
    "stella_transform_document": "executando tool de transformação Stella",
    "stella_generate_document": "executando tool de geração Stella",
    "stella_number_to_words": "executando tool de número por extenso",
    "stella_capabilities": "executando tool de capabilities Stella",
    "stella_validate_batch": "executando tool de validação em lote Stella",
}


# O modelo às vezes insiste em Markdown; o terminal não renderiza nada disso.
_BOLD = re.compile(r"(\*\*|__)")
_HEADING = re.compile(r"^#{1,6}\s+", re.MULTILINE)


def plain(text):
    """Remove marcadores de Markdown que só poluiriam o terminal."""
    if not text:
        return text
    return _HEADING.sub("", _BOLD.sub("", text))


def say(text=""):
    """Escreve uma linha no terminal usando java.io.PrintWriter."""
    STDOUT.println(text)


def write(text):
    STDOUT.write(text)
    STDOUT.flush()


def warn(text):
    """Escreve no stderr da JVM (java.lang.System.err)."""
    STDERR.println(text)


def ask(label):
    """
    Mostra o prompt e lê uma linha com java.io.BufferedReader.
    Devolve None quando a entrada termina (Ctrl+D ou stdin fechado).
    """
    write(label)
    return STDIN.readLine()


# ---------------------------------------------------------------------------
# Telas
# ---------------------------------------------------------------------------
def banner(state):
    say(LINE)
    say("              JYTHON AI AGENT")
    say(LINE)
    say()
    say("Jython : %s" % config.jython_version())
    say("Java   : %s" % config.java_version())
    say("Modelo : %s" % config.GROQ_MODEL)
    say("Tools  : %d" % len(state["registry"]))
    say("Banco  : %s" % state["database_status"])
    say("KB     : %d documentos (%d trechos)"
        % (state["knowledge"].document_count(),
           state["knowledge"].chunk_count()))
    say()
    say("Pergunte qualquer coisa. Digite /help para ver os comandos.")
    say()


def help_text(state):
    say()
    say("Comandos:")
    say("  /help    mostra esta ajuda")
    say("  /info    mostra runtime, banco e classes Java em uso")
    say("  /tools   lista as ferramentas disponíveis ao modelo")
    say("  /clear   limpa o contexto da conversa")
    say("  /stella  executa uma operação Stella localmente, sem usar a Groq")
    say("  /exit    encerra o programa")
    say()
    say("Exemplos de perguntas que acionam ferramentas:")
    say("  como esse projeto usa Jython?")
    say("  quais testes eu posso executar?")
    say("  rode os testes de fuzzy")
    say("  eu já falei sobre fuzzy antes?")
    say("  quantos tokens já usamos?")
    say("  /stella validar cpf 529.982.247-25")
    say("  /stella validar-ie SP 110.042.490.114")
    say()


def tools_text(state):
    registry = state["registry"]
    say()
    say("Ferramentas registradas (%d):" % len(registry))
    for name in registry.names():
        tool = registry.get(name)
        say("  %-26s %s" % (name, _first_sentence(tool.description)))
    say()
    say("Qualquer nome fora desta lista branca é recusado pelo registro.")
    say()


def info_text(state):
    session = state["session"]
    say()
    say("Runtime")
    say("  Jython .............. %s" % config.jython_version())
    say("  JVM ................. %s (%s)" % (config.java_version(),
                                             config.java_vm_name()))
    say()
    say("Groq")
    say("  Modelo .............. %s" % config.GROQ_MODEL)
    say("  Endpoint ............ %s" % config.GROQ_API_URL)
    say("  Chave ............... %s" % config.masked_api_key())
    say("  Raciocínio .......... %s" % config.REASONING_EFFORT)
    say("  Máx. de iterações ... %d" % config.AGENT_MAX_ITERATIONS)
    say("  Janela de contexto .. %d perguntas" % config.AGENT_CONTEXT_TURNS)
    say("  Repetições em 429 ... %d" % config.GROQ_MAX_RETRIES)
    say()
    say("Persistência")
    say("  Banco ............... %s" % state["database_status"])
    say("  Arquivo ............. %s" % config.DATABASE_PATH)
    say("  Sessão .............. %s" % (state["session_id"] or "-"))
    say()
    say("Conhecimento")
    say("  Diretório ........... %s" % config.KNOWLEDGE_DIR)
    say("  Documentos .......... %d" % state["knowledge"].document_count())
    say("  Trechos ............. %d" % state["knowledge"].chunk_count())
    say()
    say("Classes Java em uso")
    say("  Histórico ........... %s" % session.backing_class())
    say("  Mensagem ............ java.util.LinkedHashMap")
    say("  HTTP ................ java.net.URL + java.net.HttpURLConnection")
    say("  Streams ............. java.io.OutputStreamWriter / BufferedReader")
    say("  Banco ............... java.sql.DriverManager (SQLite JDBC)")
    say("  Similaridade ........ org.apache.commons.text.similarity")
    say("  Normalização ........ java.text.Normalizer")
    say("  Ambiente ............ java.lang.System.getenv()")
    say()
    say("Contexto atual: %d mensagens em %d perguntas"
        % (session.exchanged_messages(), session.turns()))
    say()


def _first_sentence(text):
    for separator in (". ", "\n"):
        if separator in text:
            return text.split(separator)[0].strip() + "."
    return text.strip()


def footer(result):
    partes = ["%.1fs" % (result.elapsed_ms / 1000.0),
              "%d chamada(s) LLM" % result.llm_calls]
    if result.tool_results:
        partes.append("tools: " + ", ".join(result.tools_used))
    usage = result.usage or {}
    if usage.get("total_tokens"):
        partes.append("%s tokens" % usage.get("total_tokens"))
    detalhes = usage.get("prompt_tokens_details") or {}
    if detalhes.get("cached_tokens"):
        partes.append("cache: %s" % detalhes.get("cached_tokens"))
    say("   [%s]" % " | ".join(partes))


# ---------------------------------------------------------------------------
# Eventos do orquestrador -> feedback no terminal
# ---------------------------------------------------------------------------
def make_event_printer():
    """Mostra o que o agente está fazendo enquanto trabalha."""

    def on_event(kind, payload):
        if kind == orchestrator_module.EVENT_TOOL_START:
            label = TOOL_LABELS.get(payload.get("name"), payload.get("name"))
            write("[%s... " % label)
        elif kind == orchestrator_module.EVENT_TOOL_END:
            if payload.get("success"):
                say("%d ms]" % payload.get("elapsed_ms", 0))
            else:
                say("falhou]")

    return on_event


def make_retry_printer():
    """Avisa o usuário quando a Groq pede para esperar (HTTP 429/5xx)."""

    def on_retry(attempt, wait_ms, status):
        say("[a Groq respondeu HTTP %d; aguardando %.1fs antes da tentativa %d]"
            % (status, wait_ms / 1000.0, attempt + 1))

    return on_retry


# ---------------------------------------------------------------------------
# Comandos
# ---------------------------------------------------------------------------
CONTINUE = 0
STOP = 1


def handle_command(command, state):
    original = command.strip()
    command = original.lower()

    if command == "/stella" or command.startswith("/stella "):
        return handle_stella_command(original, state)

    if command in ("/exit", "/quit", "/sair"):
        say()
        say("Até logo!")
        return STOP

    if command in ("/clear", "/limpar"):
        state["session"].clear()
        say()
        say("[ok] Contexto limpo. A conversa recomeça do zero.")
        say("     O histórico gravado no banco continua disponível.")
        say()
        return CONTINUE

    if command in ("/help", "/ajuda", "/?"):
        help_text(state)
        return CONTINUE

    if command == "/tools":
        tools_text(state)
        return CONTINUE

    if command == "/info":
        info_text(state)
        return CONTINUE

    say()
    say("[aviso] Comando desconhecido: %s (use /help)" % command)
    say()
    return CONTINUE


def handle_stella_command(command, state):
    """Comandos determinísticos que não enviam documento algum à Groq."""
    parts = command.split()
    service = state.get("stella")
    if service is None:
        say("[erro] Caelum Stella não está disponível neste classpath.")
        return CONTINUE
    if len(parts) < 2:
        say("Uso: /stella catalog | validar <tipo> <valor> [UF] | "
            "validar-ie <UF> <valor> | formatar <tipo> <valor> | "
            "desformatar <tipo> <valor> | gerar <tipo> | extenso <número>")
        return CONTINUE
    action = parts[1].lower()
    try:
        if action == "catalog":
            result = service.capabilities(parts[2] if len(parts) > 2 else None)
        elif action == "validar" and len(parts) >= 4:
            result = service.validate(parts[2], parts[3],
                                      parts[4] if len(parts) > 4 else None,
                                      True, True)
        elif action == "validar-ie" and len(parts) >= 4:
            result = service.validate("inscricao_estadual", parts[3], parts[2],
                                      False, True)
        elif action in ("formatar", "desformatar") and len(parts) >= 4:
            result = service.transform(parts[2],
                                       "format" if action == "formatar" else "unformat",
                                       parts[3])
        elif action == "gerar" and len(parts) >= 3:
            result = service.generate(parts[2], True)
        elif action == "extenso" and len(parts) >= 3:
            result = service.number_to_words(parts[2])
        else:
            raise StellaError("INVALID_COMMAND", "Comando Stella inválido.")
        say(json.dumps(result, ensure_ascii=False, sort_keys=True))
    except StellaError as error:
        say("[erro] %s" % error.message)
    return CONTINUE


# ---------------------------------------------------------------------------
# Bootstrap
# ---------------------------------------------------------------------------
def bootstrap():
    """Monta banco, conhecimento, ferramentas, sessão e orquestrador."""
    state = {}

    # ---- banco de dados (SQLite via JDBC) ----------------------------
    database = None
    interactions = None
    metrics = None
    session_id = None
    status = "desligado"

    try:
        database = Database(config.DATABASE_PATH).connect()
        interactions = InteractionRepository(database)
        metrics = MetricsRepository(database)
        session_id = interactions.start_session(
            config.GROQ_MODEL, config.jython_version(), config.java_version())
        status = "conectado (sessão %s)" % session_id
    except DatabaseError as error:
        warn(error.message)
        warn("       O agente continua funcionando, mas sem histórico nem "
             "métricas.")
        status = "indisponível"
    except Exception as error:
        warn("[aviso] Banco de dados indisponível: %s" % error)
        status = "indisponível"

    # ---- base de conhecimento ----------------------------------------
    knowledge = KnowledgeBase().load()

    # ---- ferramentas --------------------------------------------------
    stella = None
    try:
        stella = StellaService()
        stella.smoke_test()
    except Exception as error:
        warn("[aviso] Caelum Stella indisponível: %s" % error)

    context = ToolContext(knowledge=knowledge, interactions=interactions,
                          metrics=metrics, session_id=session_id, stella=stella)
    registry = build_registry(context)

    # ---- conversa e orquestrador --------------------------------------
    session = ChatSession()
    client = GroqClient(on_retry=make_retry_printer())
    agent = orchestrator_module.AgentOrchestrator(
        client=client, session=session, registry=registry,
        interactions=interactions, session_id=session_id,
        max_iterations=config.AGENT_MAX_ITERATIONS,
        on_event=make_event_printer())

    state.update({
        "database": database,
        "database_status": status,
        "interactions": interactions,
        "metrics": metrics,
        "session_id": session_id,
        "knowledge": knowledge,
        "registry": registry,
        "session": session,
        "client": client,
        "agent": agent,
        "stella": stella,
    })
    return state


def shutdown(state):
    """Fecha a sessão no banco e libera a conexão JDBC."""
    interactions = state.get("interactions")
    session_id = state.get("session_id")
    database = state.get("database")
    try:
        if interactions is not None and session_id is not None:
            interactions.finish_session(session_id)
    except Exception:
        pass
    try:
        if database is not None:
            database.close()
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Laço principal
# ---------------------------------------------------------------------------
def chat_loop(state):
    agent = state["agent"]
    first_read = True

    while True:
        line = ask("Você: ")

        if line is None:
            if first_read:
                say()
                say("[aviso] Nenhuma entrada disponível no terminal.")
                say("        O agente é interativo: execute o container com -it")
                say()
                say("        docker run --rm -it --env-file .env \\")
                say("            -v jython-ai-data:/app/data jython-ai-agent")
                say()
                return 1
            say()
            say("Até logo!")
            return 0

        first_read = False
        text = line.strip()

        if not text:
            continue

        if text.startswith("/"):
            if handle_command(text, state) == STOP:
                return 0
            continue

        say()
        result = agent.ask(text)

        if not result.ok:
            say()
            say(result.error)
            say()
            continue

        say()
        say("Assistente:")
        say(plain(result.content))
        say()
        footer(result)
        say()


# ---------------------------------------------------------------------------
# Entrada do programa
# ---------------------------------------------------------------------------
def main(argv):
    try:
        config.validate()
    except config.ConfigError as error:
        warn("")
        warn("[ERRO] " + error.message)
        warn("")
        return 1

    state = bootstrap()
    banner(state)

    try:
        return chat_loop(state)
    except KeyboardInterrupt:
        say()
        say("Até logo!")
        return 0
    finally:
        shutdown(state)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
