# -*- coding: utf-8 -*-
"""
Pacote ``tools`` -- as ferramentas locais que o modelo pode executar.

    registry.py       -> lista branca, validação e despacho
    knowledge_tool.py -> search_project_knowledge
    tests_tool.py     -> list_project_tests, run_project_tests
    history_tool.py   -> search_chat_history, get_recent_interactions
    metrics_tool.py   -> get_usage_metrics

O modelo nunca executa código arbitrário: ele apenas indica o nome de uma das
seis ferramentas acima, e o registro decide se aquilo pode ou não rodar.
"""
from __future__ import unicode_literals

from tools.registry import (Tool, ToolRegistry, ToolContext, ToolResult,
                            ToolError, WHITELIST)
from tools import knowledge_tool
from tools import tests_tool
from tools import history_tool
from tools import metrics_tool
from tools import stella_tool


def build_registry(context):
    """Monta o registro com as ferramentas locais e o gateway Stella."""
    registry = ToolRegistry()
    registry.register_all(knowledge_tool.create_tools(context))
    registry.register_all(tests_tool.create_tools(context))
    registry.register_all(history_tool.create_tools(context))
    registry.register_all(metrics_tool.create_tools(context))
    registry.register_all(stella_tool.create_tools(context))
    return registry


__all__ = ["Tool", "ToolRegistry", "ToolContext", "ToolResult", "ToolError",
           "WHITELIST", "build_registry", "knowledge_tool", "tests_tool",
           "history_tool", "metrics_tool", "stella_tool"]
