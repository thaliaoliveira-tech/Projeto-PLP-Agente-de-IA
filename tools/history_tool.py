# -*- coding: utf-8 -*-
"""
tools/history_tool.py -- ferramentas de memória de longo prazo:
``search_chat_history`` e ``get_recent_interactions``.

As conversas ficam no SQLite, gravadas por JDBC. A busca reaproveita
exatamente o mesmo mecanismo fuzzy da base de conhecimento, então é possível
achar uma conversa antiga mesmo escrevendo as palavras de outro jeito ou com
erros de digitação.

    SQLite -> últimas N interações -> normalização -> ranking fuzzy -> top K
"""
from __future__ import unicode_literals

import config
from search.fuzzy_matcher import rank
from tools.registry import Tool, ToolError


HISTORY_POOL = 200
HISTORY_MIN_SCORE = 0.30
ANSWER_PREVIEW = 400


def search_history_entries(repository, query, limit=None, min_score=None,
                           pool=HISTORY_POOL):
    """
    Ranqueia as interações gravadas por proximidade com a pergunta.

    Função de módulo (e não método) para que a suíte de testes possa exercitá-la
    diretamente, sem depender do agente.
    """
    if repository is None:
        return []
    if not query or not query.strip():
        return []

    limit = limit or config.HISTORY_SEARCH_LIMIT
    min_score = HISTORY_MIN_SCORE if min_score is None else min_score

    rows = repository.searchable_interactions(limit=pool)
    if not rows:
        return []

    ranked = rank(
        query,
        rows,
        text_of=lambda row: "%s %s" % (row.get("question") or "",
                                       row.get("answer") or ""),
        reference_of=lambda row: row.get("question") or "",
        top_k=limit,
        min_score=min_score,
    )

    resultados = []
    for row, score in ranked:
        resposta = row.get("answer") or ""
        resultados.append({
            "interacao": row.get("id"),
            "quando": row.get("started_at"),
            "score": round(score, 4),
            "pergunta": row.get("question"),
            "resposta": resposta[:ANSWER_PREVIEW],
        })
    return resultados


def create_tools(context):
    repository = context.interactions

    def search_chat_history(query, limit=None):
        if repository is None:
            raise ToolError("Histórico indisponível: banco de dados desligado.")

        top = limit or config.HISTORY_SEARCH_LIMIT
        if top < 1:
            top = 1
        if top > 20:
            top = 20

        resultados = search_history_entries(repository, query, limit=top)
        return {
            "consulta": query,
            "encontrados": len(resultados),
            "conversas": resultados,
            "observacao": ("Nada parecido foi encontrado no histórico."
                           if not resultados else None),
        }

    def get_recent_interactions(limit=None, scope=None):
        if repository is None:
            raise ToolError("Histórico indisponível: banco de dados desligado.")

        top = limit or 10
        if top < 1:
            top = 1
        if top > 50:
            top = 50

        session_id = context.session_id if (scope or "all") == "session" else None
        rows = repository.recent_interactions(limit=top, session_id=session_id)

        conversas = []
        for row in rows:
            resposta = row.get("answer") or ""
            conversas.append({
                "interacao": row.get("id"),
                "quando": row.get("started_at"),
                "pergunta": row.get("question"),
                "resposta": resposta[:ANSWER_PREVIEW],
            })

        return {
            "escopo": scope or "all",
            "encontrados": len(conversas),
            "conversas": conversas,
        }

    return [
        Tool(
            name="search_chat_history",
            description=(
                "Pesquisa nas conversas anteriores gravadas no banco de dados, "
                "usando busca fuzzy. Use quando o usuário perguntar se algo já "
                "foi conversado antes ou pedir para lembrar de um assunto."),
            parameters={
                "query": {
                    "type": "string",
                    "description": "Assunto procurado no histórico.",
                },
                "limit": {
                    "type": "integer",
                    "description": "Quantidade de conversas a devolver "
                                   "(1 a 20). Padrão: 5.",
                },
            },
            required=["query"],
            handler=search_chat_history,
        ),
        Tool(
            name="get_recent_interactions",
            description=(
                "Devolve as interações mais recentes, da mais nova para a mais "
                "antiga. Use quando o usuário perguntar sobre o que foi "
                "conversado recentemente, sem citar um assunto específico."),
            parameters={
                "limit": {
                    "type": "integer",
                    "description": "Quantidade de interações (1 a 50). "
                                   "Padrão: 10.",
                },
                "scope": {
                    "type": "string",
                    "enum": ["session", "all"],
                    "description": "session = apenas a execução atual; "
                                   "all = todo o histórico. Padrão: all.",
                },
            },
            required=[],
            handler=get_recent_interactions,
        ),
    ]
