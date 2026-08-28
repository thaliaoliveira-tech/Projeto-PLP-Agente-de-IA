# -*- coding: utf-8 -*-
"""
config.py -- Configuração central do Jython AI Agent.

Todas as configurações chegam ao programa por variáveis de ambiente, lidas
através da classe Java ``java.lang.System``. Ou seja: mesmo a etapa de
configuração do projeto já é um exemplo de interoperabilidade Python/Java,
porque ``System.getenv()`` é um método estático da plataforma Java sendo
invocado diretamente a partir de código Python executado pelo Jython.

APIs Java utilizadas neste módulo:

    java.lang.System.getenv()      -> variáveis de ambiente
    java.lang.System.getProperty() -> propriedades da JVM (versão do Java, etc.)
"""
from __future__ import unicode_literals

import os
import sys

# ---------------------------------------------------------------------------
# Import de uma classe Java a partir de código Python. Só é possível porque
# este arquivo é executado pelo Jython, sobre a JVM.
# ---------------------------------------------------------------------------
from java.lang import System


# Raiz do projeto (dentro do container: /app).
BASE_DIR = os.path.dirname(os.path.abspath(__file__))


# ---------------------------------------------------------------------------
# Valores padrão
# ---------------------------------------------------------------------------
DEFAULT_MODEL = "openai/gpt-oss-120b"
DEFAULT_API_URL = "https://api.groq.com/openai/v1/chat/completions"

DEFAULT_SYSTEM_PROMPT = (
    "Você é o assistente do Jython AI Agent, um projeto acadêmico escrito em "
    "Python e executado pelo Jython sobre a JVM, que usa APIs Java para rede, "
    "streams, coleções e banco de dados.\n"
    "\n"
    "REGRAS DE USO DAS FERRAMENTAS:\n"
    "1. Quando a pergunta for sobre este projeto (arquitetura, arquivos, "
    "Jython, Java, Groq, Docker, banco de dados, tools, testes, configuração "
    "ou funcionamento interno), NÃO responda apenas com conhecimento próprio: "
    "chame search_project_knowledge antes de responder.\n"
    "2. Quando o usuário pedir para listar testes, use list_project_tests.\n"
    "3. Quando o usuário pedir para executar testes, use run_project_tests.\n"
    "4. Quando o usuário perguntar sobre conversas anteriores, use "
    "search_chat_history ou get_recent_interactions.\n"
    "5. Quando o usuário perguntar sobre tokens, cache, latência ou uso, use "
    "get_usage_metrics.\n"
    "6. NUNCA invente resultados de ferramentas nem números de métricas: se "
    "precisar de um dado, chame a ferramenta correspondente.\n"
    "7. Depois de executar uma ferramenta, transforme o resultado em uma "
    "resposta clara para humanos; não devolva JSON cru ao usuário.\n"
    "8. Para validar CPF, CNPJ, NIT, RENAVAM, título eleitoral ou inscrição "
    "estadual, use stella_validate_document; não calcule dígitos por conta própria.\n"
    "9. Para formatar ou remover máscara desses documentos, use "
    "stella_transform_document. Para descobrir operações, use "
    "stella_capabilities.\n"
    "\n"
    "ESTILO DA RESPOSTA: escreva em português do Brasil, em TEXTO PURO. "
    "A resposta é exibida em um terminal, então NÃO use Markdown: nada de "
    "asteriscos, crases, cabeçalhos com # nem tabelas. Para listas, use "
    "hífen ou numeração simples. "
    "Seja direto e objetivo."
)


class ConfigError(Exception):
    """Erro de configuração, com mensagem amigável para o usuário final."""

    def __init__(self, message):
        Exception.__init__(self, message)
        self.message = message


# ---------------------------------------------------------------------------
# Leitura de variáveis de ambiente via java.lang.System
# ---------------------------------------------------------------------------
def env(name, default=None):
    """Lê uma variável de ambiente usando a API Java ``java.lang.System``."""
    value = System.getenv(name)
    if value is None:
        return default
    value = value.strip()
    if value == "":
        return default
    return value


def _env_float(name, default):
    raw = env(name)
    if raw is None:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def _env_int(name, default):
    raw = env(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


# ---------------------------------------------------------------------------
# Groq / LLM
# ---------------------------------------------------------------------------
GROQ_API_KEY = env("GROQ_API_KEY")
GROQ_MODEL = env("GROQ_MODEL", DEFAULT_MODEL)
GROQ_API_URL = env("GROQ_API_URL", DEFAULT_API_URL)
SYSTEM_PROMPT = env("GROQ_SYSTEM_PROMPT", DEFAULT_SYSTEM_PROMPT)

# 1.0 é o valor recomendado para o gpt-oss. Temperaturas baixas fazem modelos
# de raciocínio degenerarem em repetição quando o contexto tem respostas
# parecidas -- comportamento reproduzido e corrigido neste projeto.
TEMPERATURE = _env_float("GROQ_TEMPERATURE", 1.0)
MAX_COMPLETION_TOKENS = _env_int("GROQ_MAX_TOKENS", 1500)

CONNECT_TIMEOUT_MS = _env_int("GROQ_CONNECT_TIMEOUT_MS", 15000)
READ_TIMEOUT_MS = _env_int("GROQ_READ_TIMEOUT_MS", 120000)

# Esforço de raciocínio do gpt-oss: low, medium ou high.
# O modelo SEMPRE raciocina; o que muda é quanto. Raciocinar mais custa tokens
# de saída e latência, mas "low" degrada visivelmente a qualidade da resposta
# neste caso de uso (o modelo se atrapalha ao resumir resultados de
# ferramenta), então o padrão é "medium".
REASONING_EFFORT = env("GROQ_REASONING_EFFORT", "medium")

# Repetição automática de erros temporários (HTTP 429 e 5xx).
GROQ_MAX_RETRIES = _env_int("GROQ_MAX_RETRIES", 3)
GROQ_RETRY_MAX_WAIT_MS = _env_int("GROQ_RETRY_MAX_WAIT_MS", 30000)


# ---------------------------------------------------------------------------
# Agente
# ---------------------------------------------------------------------------
AGENT_MAX_ITERATIONS = _env_int("AGENT_MAX_ITERATIONS", 5)

# Janela de contexto: quantas perguntas anteriores continuam sendo reenviadas
# à LLM. Sem esse limite, o histórico cresce sem parar e cada pergunta fica
# mais cara que a anterior -- até estourar o limite de tokens por minuto.
AGENT_CONTEXT_TURNS = _env_int("AGENT_CONTEXT_TURNS", 4)

# Caelum Stella: proteção contra entradas excessivas e lotes muito grandes.
STELLA_BATCH_MAX_ITEMS = _env_int("STELLA_BATCH_MAX_ITEMS", 100)
STELLA_INPUT_MAX_LENGTH = _env_int("STELLA_INPUT_MAX_LENGTH", 64)


# ---------------------------------------------------------------------------
# Banco de dados (SQLite via JDBC)
# ---------------------------------------------------------------------------
DATABASE_PATH = env("DATABASE_PATH",
                    os.path.join(BASE_DIR, "data", "jython_ai_chat.db"))


# ---------------------------------------------------------------------------
# Base de conhecimento e busca fuzzy
# ---------------------------------------------------------------------------
KNOWLEDGE_DIR = env("KNOWLEDGE_DIR", os.path.join(BASE_DIR, "knowledge"))
KNOWLEDGE_TOP_K = _env_int("KNOWLEDGE_TOP_K", 3)
KNOWLEDGE_MIN_SCORE = _env_float("KNOWLEDGE_MIN_SCORE", 0.35)
KNOWLEDGE_MAX_CHARS = _env_int("KNOWLEDGE_MAX_CHARS", 700)

HISTORY_SEARCH_LIMIT = _env_int("HISTORY_SEARCH_LIMIT", 5)


# ---------------------------------------------------------------------------
# Validação
# ---------------------------------------------------------------------------
MISSING_KEY_MESSAGE = (
    "GROQ_API_KEY não encontrada.\n"
    "\n"
    "A chave é lida do ambiente por java.lang.System.getenv(\"GROQ_API_KEY\").\n"
    "\n"
    "Crie o arquivo .env na raiz do projeto:\n"
    "\n"
    "    GROQ_API_KEY=gsk_sua_chave_aqui\n"
    "    GROQ_MODEL=openai/gpt-oss-120b\n"
    "\n"
    "E execute o container passando esse arquivo:\n"
    "\n"
    "    docker run --rm -it --env-file .env \\\n"
    "        -v jython-ai-data:/app/data jython-ai-agent"
)


def validate():
    """Garante que a configuração mínima existe; lança ConfigError se não existir."""
    if not GROQ_API_KEY:
        raise ConfigError(MISSING_KEY_MESSAGE)
    return True


# ---------------------------------------------------------------------------
# Informações de runtime (usadas no banner do agente)
# ---------------------------------------------------------------------------
def jython_version():
    """Versão do Jython em execução (ex.: 2.7.4)."""
    return sys.version.split(" ")[0]


def java_version():
    """Versão da JVM, obtida via java.lang.System.getProperty()."""
    return System.getProperty("java.version")


def java_vm_name():
    """Nome da JVM em execução."""
    return System.getProperty("java.vm.name")


def masked_api_key():
    """Versão mascarada da chave -- segura para exibir no terminal."""
    if not GROQ_API_KEY:
        return "(ausente)"
    if len(GROQ_API_KEY) <= 8:
        return "****"
    return GROQ_API_KEY[:4] + "*" * 8 + GROQ_API_KEY[-4:]
    return GROQ_API_KEY[:4] + "*" * 8 + GROQ_API_KEY[-4:]
