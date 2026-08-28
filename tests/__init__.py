# -*- coding: utf-8 -*-
"""
Pacote ``tests`` -- suíte automatizada do Jython AI Agent.

    registry.py         -> catálogo (T01..T15, T90) e executor
    test_chat.py        -> histórico da conversa em coleções Java
    test_groq_client.py -> payload, tool_calls e integração real (T90)
    test_tools.py       -> registro e lista branca de ferramentas
    test_knowledge.py   -> busca fuzzy na base de conhecimento
    test_database.py    -> SQLite via JDBC
    test_metrics.py     -> métricas e busca no histórico

Os testes são executados pelo próprio agente através das ferramentas
``list_project_tests`` e ``run_project_tests``.
"""
