# -*- coding: utf-8 -*-
"""
database/metrics_repository.py -- observabilidade de LLM.

Todas as estatísticas saem de funções de agregação SQL (COUNT, SUM, AVG, MIN,
MAX) executadas pelo driver JDBC sobre as tabelas ``llm_calls`` e
``tool_executions``.

Escopos aceitos:

    session -> apenas a sessão atual
    all     -> todo o histórico do banco
    last_n  -> as N chamadas mais recentes
"""
from __future__ import unicode_literals


SCOPES = ("session", "all", "last_n")

_AGGREGATES = (
    "COUNT(*) AS calls, "
    "SUM(prompt_tokens) AS input_total, "
    "AVG(prompt_tokens) AS input_avg, "
    "MIN(prompt_tokens) AS input_min, "
    "MAX(prompt_tokens) AS input_max, "
    "SUM(completion_tokens) AS output_total, "
    "AVG(completion_tokens) AS output_avg, "
    "MIN(completion_tokens) AS output_min, "
    "MAX(completion_tokens) AS output_max, "
    "SUM(total_tokens) AS tokens_total, "
    "AVG(total_tokens) AS tokens_avg, "
    "MIN(total_tokens) AS tokens_min, "
    "MAX(total_tokens) AS tokens_max, "
    "SUM(cached_tokens) AS cached_total, "
    "SUM(local_elapsed_ms) AS latency_total, "
    "AVG(local_elapsed_ms) AS latency_avg, "
    "MIN(local_elapsed_ms) AS latency_min, "
    "MAX(local_elapsed_ms) AS latency_max, "
    "AVG(groq_total_time_ms) AS groq_time_avg"
)


class MetricsRepository(object):
    """Consultas agregadas de tokens, cache, latência e ferramentas."""

    def __init__(self, database):
        self.database = database

    # ------------------------------------------------------------------
    # Métricas de uso da LLM
    # ------------------------------------------------------------------
    def usage_metrics(self, scope="session", session_id=None, limit=10):
        scope = (scope or "session").lower()
        if scope not in SCOPES:
            scope = "session"

        if scope == "all":
            sql = "SELECT %s FROM llm_calls" % _AGGREGATES
            parameters = ()
        elif scope == "last_n":
            sql = ("SELECT %s FROM (SELECT * FROM llm_calls "
                   "ORDER BY id DESC LIMIT ?)" % _AGGREGATES)
            parameters = (int(limit),)
        else:
            sql = ("SELECT %s FROM llm_calls WHERE interaction_id IN "
                   "(SELECT id FROM interactions WHERE session_id = ?)"
                   % _AGGREGATES)
            parameters = (session_id,)

        rows = self.database.query(sql, parameters)
        row = rows[0] if rows else {}
        calls = _int(row.get("calls"))

        metrics = {
            "scope": scope,
            "llm_calls": calls,
            "input_tokens": _block(row, "input"),
            "output_tokens": _block(row, "output"),
            "total_tokens": _block(row, "tokens"),
            "latency_ms": _block(row, "latency"),
            "cache": self._cache_block(row),
            "groq_time_avg_ms": _round(row.get("groq_time_avg")),
            "tools": self.tool_metrics(scope=scope, session_id=session_id,
                                       limit=limit),
            "interactions": self.count_interactions(scope, session_id),
        }
        return metrics

    def _cache_block(self, row):
        cached = _int(row.get("cached_total"))
        prompt = _int(row.get("input_total"))
        rate = (float(cached) / prompt * 100.0) if prompt else 0.0
        return {
            "cached_tokens": cached,
            "prompt_tokens": prompt,
            "cache_hit_rate": round(rate, 2),
        }

    # ------------------------------------------------------------------
    # Métricas de ferramentas
    # ------------------------------------------------------------------
    def tool_metrics(self, scope="session", session_id=None, limit=10):
        where, parameters = self._tool_filter(scope, session_id, limit)

        rows = self.database.query(
            "SELECT COUNT(*) AS total, "
            "SUM(CASE WHEN success = 0 THEN 1 ELSE 0 END) AS failures, "
            "AVG(elapsed_ms) AS avg_ms "
            "FROM tool_executions" + where, parameters)
        row = rows[0] if rows else {}

        top = self.database.query(
            "SELECT tool_name, COUNT(*) AS uses FROM tool_executions" + where +
            " GROUP BY tool_name ORDER BY uses DESC LIMIT 5", parameters)

        interactions = self.count_interactions(scope, session_id)
        total = _int(row.get("total"))
        per_interaction = (float(total) / interactions) if interactions else 0.0

        return {
            "total_calls": total,
            "failures": _int(row.get("failures")),
            "avg_elapsed_ms": _round(row.get("avg_ms")),
            "avg_per_interaction": round(per_interaction, 2),
            "most_used": top[0]["tool_name"] if top else None,
            "ranking": [{"tool": item["tool_name"], "uses": _int(item["uses"])}
                        for item in top],
        }

    def _tool_filter(self, scope, session_id, limit):
        if scope == "all":
            return "", ()
        if scope == "last_n":
            return (" WHERE id IN (SELECT id FROM tool_executions "
                    "ORDER BY id DESC LIMIT ?)", (int(limit),))
        return (" WHERE interaction_id IN (SELECT id FROM interactions "
                "WHERE session_id = ?)", (session_id,))

    # ------------------------------------------------------------------
    # Auxiliares
    # ------------------------------------------------------------------
    def count_interactions(self, scope="session", session_id=None):
        if scope == "all" or session_id is None:
            return _int(self.database.scalar(
                "SELECT COUNT(*) AS total FROM interactions", (), 0))
        return _int(self.database.scalar(
            "SELECT COUNT(*) AS total FROM interactions WHERE session_id = ?",
            (session_id,), 0))

    def count_llm_calls(self):
        return _int(self.database.scalar(
            "SELECT COUNT(*) AS total FROM llm_calls", (), 0))


# ---------------------------------------------------------------------------
# Conversões seguras (as agregações devolvem NULL quando não há linhas)
# ---------------------------------------------------------------------------
def _int(value, default=0):
    if value is None:
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _round(value, digits=2, default=0.0):
    if value is None:
        return default
    try:
        return round(float(value), digits)
    except (TypeError, ValueError):
        return default


def _block(row, prefix):
    return {
        "total": _int(row.get(prefix + "_total")),
        "avg": _round(row.get(prefix + "_avg")),
        "min": _int(row.get(prefix + "_min")),
        "max": _int(row.get(prefix + "_max")),
    }
