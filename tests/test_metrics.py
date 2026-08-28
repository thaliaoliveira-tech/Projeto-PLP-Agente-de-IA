# -*- coding: utf-8 -*-
"""
tests/test_metrics.py -- métricas de uso (T13) e busca fuzzy no histórico (T14).

Como em test_database.py, cada teste usa um banco temporário próprio.
"""
from __future__ import unicode_literals

import unittest

from java.io import File

from database.connection import Database
from database.interaction_repository import InteractionRepository
from database.metrics_repository import MetricsRepository
from tests.test_database import temp_database_path
from tools.history_tool import search_history_entries


class FakeReply(object):
    """Resposta da Groq simulada, para não gastar tokens nos testes."""

    def __init__(self, prompt, completion, cached, elapsed_ms):
        self.model = "openai/gpt-oss-120b"
        self.finish_reason = "stop"
        self.elapsed_ms = elapsed_ms
        self.usage = {
            "prompt_tokens": prompt,
            "completion_tokens": completion,
            "total_tokens": prompt + completion,
            "prompt_tokens_details": {"cached_tokens": cached},
            "queue_time": 0.02,
            "prompt_time": 0.11,
            "completion_time": 0.30,
            "total_time": 0.43,
        }


class MetricsTest(unittest.TestCase):

    def setUp(self):
        self.path = temp_database_path()
        self.database = Database(self.path).connect()
        self.interactions = InteractionRepository(self.database)
        self.metrics = MetricsRepository(self.database)

    def tearDown(self):
        self.database.close()
        arquivo = File(self.path)
        if arquivo.exists():
            arquivo.delete()

    # T13 -----------------------------------------------------------------
    def test_usage_metrics(self):
        session_id = self.interactions.start_session(
            "openai/gpt-oss-120b", "2.7.4", "11")
        interaction_id = self.interactions.start_interaction(session_id)

        self.interactions.save_llm_call(
            interaction_id, 0, FakeReply(1000, 100, 400, 800))
        self.interactions.save_llm_call(
            interaction_id, 1, FakeReply(500, 50, 100, 400))
        self.interactions.save_tool_execution(
            interaction_id, "call_1", "search_project_knowledge",
            {"query": "docker"}, {"encontrados": 3}, 12, True, None)
        self.interactions.finish_interaction(interaction_id, 1200, "ok")

        metricas = self.metrics.usage_metrics(scope="session",
                                              session_id=session_id)

        self.assertEqual(2, metricas["llm_calls"])

        entrada = metricas["input_tokens"]
        self.assertEqual(1500, entrada["total"])
        self.assertEqual(750.0, entrada["avg"])
        self.assertEqual(500, entrada["min"])
        self.assertEqual(1000, entrada["max"])

        saida = metricas["output_tokens"]
        self.assertEqual(150, saida["total"])
        self.assertEqual(75.0, saida["avg"])

        total = metricas["total_tokens"]
        self.assertEqual(1650, total["total"])

        latencia = metricas["latency_ms"]
        self.assertEqual(1200, latencia["total"])
        self.assertEqual(600.0, latencia["avg"])
        self.assertEqual(400, latencia["min"])
        self.assertEqual(800, latencia["max"])

        cache = metricas["cache"]
        self.assertEqual(500, cache["cached_tokens"])
        self.assertEqual(1500, cache["prompt_tokens"])
        self.assertEqual(33.33, cache["cache_hit_rate"])

        ferramentas = metricas["tools"]
        self.assertEqual(1, ferramentas["total_calls"])
        self.assertEqual(0, ferramentas["failures"])
        self.assertEqual("search_project_knowledge", ferramentas["most_used"])

        # O escopo "all" enxerga os mesmos dados neste banco isolado.
        todas = self.metrics.usage_metrics(scope="all")
        self.assertEqual(2, todas["llm_calls"])
        self.assertEqual("all", todas["scope"])


class HistorySearchTest(unittest.TestCase):

    def setUp(self):
        self.path = temp_database_path()
        self.database = Database(self.path).connect()
        self.interactions = InteractionRepository(self.database)

        self.session_id = self.interactions.start_session(
            "openai/gpt-oss-120b", "2.7.4", "11")
        self._save("java tem fuzzy matching?",
                   "Sim. Podemos usar similaridade textual do Apache Commons "
                   "Text para localizar documentos relevantes.")
        self._save("como subo o container?",
                   "Use docker run com o volume de dados montado em /app/data.")

    def tearDown(self):
        self.database.close()
        arquivo = File(self.path)
        if arquivo.exists():
            arquivo.delete()

    def _save(self, pergunta, resposta):
        interaction_id = self.interactions.start_interaction(self.session_id)
        self.interactions.save_message(self.session_id, interaction_id,
                                       "user", pergunta)
        self.interactions.save_message(self.session_id, interaction_id,
                                       "assistant", resposta)
        self.interactions.finish_interaction(interaction_id, 500, "ok")

    # T14 -----------------------------------------------------------------
    def test_history_fuzzy_search(self):
        encontrados = search_history_entries(
            self.interactions, "falamos sobre fuzy matchng em java?", limit=3)

        self.assertTrue(len(encontrados) > 0,
                        "a busca fuzzy no histórico não achou nada")
        self.assertEqual("java tem fuzzy matching?",
                         encontrados[0]["pergunta"])
        self.assertTrue(encontrados[0]["score"] > 0.3)

        # Uma pergunta sobre outro assunto recupera a outra conversa.
        containers = search_history_entries(
            self.interactions, "o que falamos sobre container e volume?",
            limit=3)
        self.assertEqual("como subo o container?",
                         containers[0]["pergunta"])
