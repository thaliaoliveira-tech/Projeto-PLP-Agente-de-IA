# -*- coding: utf-8 -*-
"""
database/schema.py -- DDL do banco de dados.

Cinco tabelas deixam a execução do agente inteiramente auditável:

    sessions        -> uma linha por execução do programa
    interactions    -> uma linha por pergunta completa do usuário
    messages        -> uma linha por mensagem (system/user/assistant/tool)
    llm_calls       -> uma linha por chamada à Groq (uma pergunta pode gerar
                       várias, por causa das ferramentas)
    tool_executions -> uma linha por ferramenta executada
"""
from __future__ import unicode_literals


STATEMENTS = [
    """
    CREATE TABLE IF NOT EXISTS sessions (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        started_at      TEXT NOT NULL,
        finished_at     TEXT,
        model           TEXT,
        jython_version  TEXT,
        java_version    TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS interactions (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id   INTEGER NOT NULL,
        started_at   TEXT NOT NULL,
        finished_at  TEXT,
        elapsed_ms   INTEGER,
        status       TEXT,
        error        TEXT,
        FOREIGN KEY (session_id) REFERENCES sessions (id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS messages (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id      INTEGER NOT NULL,
        interaction_id  INTEGER,
        role            TEXT NOT NULL,
        content         TEXT,
        created_at      TEXT NOT NULL,
        FOREIGN KEY (session_id) REFERENCES sessions (id),
        FOREIGN KEY (interaction_id) REFERENCES interactions (id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS llm_calls (
        id                  INTEGER PRIMARY KEY AUTOINCREMENT,
        interaction_id      INTEGER NOT NULL,
        call_index          INTEGER NOT NULL,
        model               TEXT,
        prompt_tokens       INTEGER DEFAULT 0,
        completion_tokens   INTEGER DEFAULT 0,
        total_tokens        INTEGER DEFAULT 0,
        cached_tokens       INTEGER DEFAULT 0,
        queue_time_ms       REAL DEFAULT 0,
        prompt_time_ms      REAL DEFAULT 0,
        completion_time_ms  REAL DEFAULT 0,
        groq_total_time_ms  REAL DEFAULT 0,
        local_elapsed_ms    INTEGER DEFAULT 0,
        http_attempts       INTEGER DEFAULT 1,
        retry_wait_ms       INTEGER DEFAULT 0,
        finish_reason       TEXT,
        created_at          TEXT NOT NULL,
        FOREIGN KEY (interaction_id) REFERENCES interactions (id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS tool_executions (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        interaction_id  INTEGER NOT NULL,
        tool_call_id    TEXT,
        tool_name       TEXT NOT NULL,
        arguments_json  TEXT,
        result_json     TEXT,
        elapsed_ms      INTEGER DEFAULT 0,
        success         INTEGER DEFAULT 1,
        error           TEXT,
        created_at      TEXT NOT NULL,
        FOREIGN KEY (interaction_id) REFERENCES interactions (id)
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_messages_interaction ON messages (interaction_id)",
    "CREATE INDEX IF NOT EXISTS idx_messages_role ON messages (role)",
    "CREATE INDEX IF NOT EXISTS idx_llm_calls_interaction ON llm_calls (interaction_id)",
    "CREATE INDEX IF NOT EXISTS idx_tools_interaction ON tool_executions (interaction_id)",
    "CREATE INDEX IF NOT EXISTS idx_interactions_session ON interactions (session_id)",
]


TABLES = ["sessions", "interactions", "messages", "llm_calls", "tool_executions"]


# ---------------------------------------------------------------------------
# Migrações
#
# As tabelas são criadas com CREATE TABLE IF NOT EXISTS, então um banco antigo
# (de um volume Docker já existente) não ganharia colunas novas sozinho. Estas
# colunas são adicionadas na abertura da conexão, quando ainda não existirem.
# ---------------------------------------------------------------------------
MIGRATIONS = [
    ("interactions", "error", "ALTER TABLE interactions ADD COLUMN error TEXT"),
    ("llm_calls", "http_attempts",
     "ALTER TABLE llm_calls ADD COLUMN http_attempts INTEGER DEFAULT 1"),
    ("llm_calls", "retry_wait_ms",
     "ALTER TABLE llm_calls ADD COLUMN retry_wait_ms INTEGER DEFAULT 0"),
]
