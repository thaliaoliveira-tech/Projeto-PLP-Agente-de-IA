# -*- coding: utf-8 -*-
"""
tools/metrics_tool.py -- ferramenta ``get_usage_metrics``.

Observabilidade de LLM: tokens de entrada e saída, taxa de acerto do prompt
cache, latência e uso das ferramentas. Todos os números saem de agregações SQL
(COUNT, SUM, AVG, MIN, MAX) executadas por JDBC sobre a tabela ``llm_calls``.
"""
from __future__ import unicode_literals

from tools.registry import Tool, ToolError


def create_tools(context):
    metrics = context.metrics

    def get_usage_metrics(scope=None, limit=None):
        if metrics is None:
            raise ToolError("Métricas indisponíveis: banco de dados desligado.")

        scope = (scope or "session").lower()
        top = limit or 10
        if top < 1:
            top = 1
        if top > 500:
            top = 500

        dados = metrics.usage_metrics(scope=scope,
                                      session_id=context.session_id,
                                      limit=top)

        cache = dados["cache"]
        dados["resumo"] = (
            "%d chamadas à LLM em %d interações; entrada %d tokens "
            "(média %.0f), saída %d tokens (média %.0f), cache %.2f%%, "
            "latência média %.0f ms."
            % (dados["llm_calls"], dados["interactions"],
               dados["input_tokens"]["total"], dados["input_tokens"]["avg"],
               dados["output_tokens"]["total"], dados["output_tokens"]["avg"],
               cache["cache_hit_rate"], dados["latency_ms"]["avg"]))

        if dados["llm_calls"] == 0:
            dados["observacao"] = ("Ainda não há chamadas registradas neste "
                                   "escopo.")
        return dados

    return [Tool(
        name="get_usage_metrics",
        description=(
            "Devolve as métricas de uso registradas no banco: quantidade de "
            "chamadas à LLM, tokens de entrada e de saída (total, média, "
            "mínimo e máximo), tokens vindos do prompt cache com a taxa de "
            "acerto, latência e estatísticas de uso das ferramentas. Use "
            "sempre que o usuário perguntar sobre tokens, cache, latência, "
            "custo ou uso do agente."),
        parameters={
            "scope": {
                "type": "string",
                "enum": ["session", "all", "last_n"],
                "description": "session = execução atual; all = todo o "
                               "histórico; last_n = as últimas N chamadas. "
                               "Padrão: session.",
            },
            "limit": {
                "type": "integer",
                "description": "Usado apenas com scope=last_n. Padrão: 10.",
            },
        },
        required=[],
        handler=get_usage_metrics,
    )]
