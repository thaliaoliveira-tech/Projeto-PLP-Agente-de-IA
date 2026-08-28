# -*- coding: utf-8 -*-
"""
database/interaction_repository.py -- gravação e leitura do histórico.

Registra sessões, interações, mensagens, chamadas à LLM e execuções de
ferramentas. Tudo o que o agente faz fica auditável no banco.

A data/hora é obtida com ``java.time.LocalDateTime``, mais uma API Java usada
diretamente pelo código Python.
"""
from __future__ import unicode_literals

import json

from java.time import LocalDateTime
from java.time.format import DateTimeFormatter


_FORMATTER = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss")


def now():
    """Data/hora atual formatada, via java.time."""
    return LocalDateTime.now().format(_FORMATTER)


class InteractionRepository(object):
    """Persistência das conversas do agente."""

    def __init__(self, database):
        self.database = database

    # ------------------------------------------------------------------
    # Sessões
    # ------------------------------------------------------------------
    def start_session(self, model, jython_version, java_version):
        return self.database.insert(
            "INSERT INTO sessions (started_at, model, jython_version, "
            "java_version) VALUES (?, ?, ?, ?)",
            (now(), model, jython_version, java_version))

    def finish_session(self, session_id):
        self.database.execute(
            "UPDATE sessions SET finished_at = ? WHERE id = ?",
            (now(), session_id))

    def count_sessions(self):
        return self.database.scalar(
            "SELECT COUNT(*) AS total FROM sessions", (), 0)

    # ------------------------------------------------------------------
    # Interações
    # ------------------------------------------------------------------
    def start_interaction(self, session_id):
        return self.database.insert(
            "INSERT INTO interactions (session_id, started_at, status) "
            "VALUES (?, ?, ?)",
            (session_id, now(), "running"))

    def finish_interaction(self, interaction_id, elapsed_ms, status="ok",
                           error=None):
        self.database.execute(
            "UPDATE interactions SET finished_at = ?, elapsed_ms = ?, "
            "status = ?, error = ? WHERE id = ?",
            (now(), int(elapsed_ms), status, error, interaction_id))

    # ------------------------------------------------------------------
    # Mensagens
    # ------------------------------------------------------------------
    def save_message(self, session_id, interaction_id, role, content):
        return self.database.insert(
            "INSERT INTO messages (session_id, interaction_id, role, content, "
            "created_at) VALUES (?, ?, ?, ?, ?)",
            (session_id, interaction_id, role, content, now()))

    def count_messages(self, role=None):
        if role is None:
            return self.database.scalar(
                "SELECT COUNT(*) AS total FROM messages", (), 0)
        return self.database.scalar(
            "SELECT COUNT(*) AS total FROM messages WHERE role = ?", (role,), 0)

    # ------------------------------------------------------------------
    # Chamadas à LLM
    # ------------------------------------------------------------------
    def save_llm_call(self, interaction_id, call_index, reply):
        """Grava uma chamada à Groq a partir de um ``GroqReply``."""
        usage = reply.usage or {}
        details = usage.get("prompt_tokens_details") or {}
        cached = details.get("cached_tokens", 0) or 0

        return self.database.insert(
            "INSERT INTO llm_calls (interaction_id, call_index, model, "
            "prompt_tokens, completion_tokens, total_tokens, cached_tokens, "
            "queue_time_ms, prompt_time_ms, completion_time_ms, "
            "groq_total_time_ms, local_elapsed_ms, http_attempts, "
            "retry_wait_ms, finish_reason, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (interaction_id,
             call_index,
             reply.model,
             int(usage.get("prompt_tokens", 0) or 0),
             int(usage.get("completion_tokens", 0) or 0),
             int(usage.get("total_tokens", 0) or 0),
             int(cached),
             _seconds_to_ms(usage.get("queue_time")),
             _seconds_to_ms(usage.get("prompt_time")),
             _seconds_to_ms(usage.get("completion_time")),
             _seconds_to_ms(usage.get("total_time")),
             int(reply.elapsed_ms or 0),
             int(getattr(reply, "attempts", 1) or 1),
             int(getattr(reply, "retry_wait_ms", 0) or 0),
             reply.finish_reason,
             now()))

    # ------------------------------------------------------------------
    # Execuções de ferramentas
    # ------------------------------------------------------------------
    def save_tool_execution(self, interaction_id, tool_call_id, tool_name,
                            arguments, result, elapsed_ms, success=True,
                            error=None):
        return self.database.insert(
            "INSERT INTO tool_executions (interaction_id, tool_call_id, "
            "tool_name, arguments_json, result_json, elapsed_ms, success, "
            "error, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (interaction_id,
             tool_call_id,
             tool_name,
             _as_json(arguments),
             _as_json(result),
             int(elapsed_ms or 0),
             1 if success else 0,
             error,
             now()))

    # ------------------------------------------------------------------
    # Consulta do histórico
    # ------------------------------------------------------------------
    def recent_interactions(self, limit=10, session_id=None):
        """
        Últimas interações com pergunta e resposta, da mais nova para a mais
        antiga.
        """
        sql = (
            "SELECT i.id AS id, i.started_at AS started_at, "
            "       i.elapsed_ms AS elapsed_ms, i.status AS status, "
            "       i.session_id AS session_id, "
            "       (SELECT m.content FROM messages m "
            "         WHERE m.interaction_id = i.id AND m.role = 'user' "
            "         ORDER BY m.id LIMIT 1) AS question, "
            "       (SELECT m.content FROM messages m "
            "         WHERE m.interaction_id = i.id AND m.role = 'assistant' "
            "           AND m.content IS NOT NULL AND m.content <> '' "
            "         ORDER BY m.id DESC LIMIT 1) AS answer "
            "FROM interactions i ")
        parameters = []
        if session_id is not None:
            sql += "WHERE i.session_id = ? "
            parameters.append(session_id)
        sql += "ORDER BY i.id DESC LIMIT ?"
        parameters.append(int(limit) * 3 + 10)

        rows = self.database.query(sql, tuple(parameters))
        useful = [row for row in rows if row.get("question")]
        return useful[:int(limit)]

    def searchable_interactions(self, limit=200):
        """Interações candidatas para a busca fuzzy no histórico."""
        return self.recent_interactions(limit=limit)

    def interaction_messages(self, interaction_id):
        return self.database.query(
            "SELECT id, role, content, created_at FROM messages "
            "WHERE interaction_id = ? ORDER BY id", (interaction_id,))


def _as_json(value):
    if value is None:
        return None
    if isinstance(value, basestring):
        return value
    try:
        return json.dumps(value, ensure_ascii=False)
    except (TypeError, ValueError):
        return unicode(value)


def _seconds_to_ms(value):
    """A Groq informa tempos em segundos (float); guardamos em milissegundos."""
    if value is None:
        return 0.0
    try:
        return float(value) * 1000.0
    except (TypeError, ValueError):
        return 0.0

        if role is not None:
            msgs_where.append("role = ?")
            params_m.append(role)
        else:
            msgs_where.append("role IN ('user', 'assistant')")

        sql_msgs = (
            "SELECT id, session_id, interaction_id, role, content, created_at "
            "FROM messages WHERE %s "
            "ORDER BY id ASC" % " AND ".join(msgs_where))

        return self.database.query(sql_msgs, tuple(params_m))


def _as_json(value):
    if value is None:
        return None
    if isinstance(value, basestring):
        return value
    try:
        return json.dumps(value, ensure_ascii=False)
    except (TypeError, ValueError):
        return unicode(value)


def _seconds_to_ms(value):
    """A Groq informa tempos em segundos (float); guardamos em milissegundos."""
    if value is None:
        return 0.0
    try:
        return float(value) * 1000.0
    except (TypeError, ValueError):
        return 0.0
