# -*- coding: utf-8 -*-
"""
tests/test_database.py -- SQLite via JDBC (T11, T12).

Os testes nunca tocam o banco de produção: cada execução cria um arquivo
temporário com nome aleatório (java.util.UUID) e o apaga no final.
"""
from __future__ import unicode_literals

import unittest

from java.io import File
from java.lang import System
from java.util import UUID

from database import schema
from database.connection import Database
from database.interaction_repository import InteractionRepository


def temp_database_path():
    """Caminho temporário exclusivo, em java.io.tmpdir."""
    return "%s%sjython-ai-tests-%s.db" % (
        System.getProperty("java.io.tmpdir"),
        File.separator,
        UUID.randomUUID().toString())


class DatabaseTest(unittest.TestCase):

    def setUp(self):
        self.path = temp_database_path()
        self.database = Database(self.path).connect()
        self.repository = InteractionRepository(self.database)

    def tearDown(self):
        self.database.close()
        arquivo = File(self.path)
        if arquivo.exists():
            arquivo.delete()

    # T11 -----------------------------------------------------------------
    def test_schema_tables(self):
        tabelas = self.database.table_names()
        for esperada in schema.TABLES:
            self.assertIn(esperada, tabelas,
                          "tabela ausente no schema: %s" % esperada)
        self.assertEqual(5, len(schema.TABLES))

    # T12 -----------------------------------------------------------------
    def test_interaction_roundtrip(self):
        session_id = self.repository.start_session(
            "openai/gpt-oss-120b", "2.7.4", "11")
        self.assertTrue(session_id > 0)

        interaction_id = self.repository.start_interaction(session_id)
        self.repository.save_message(session_id, interaction_id, "user",
                                     "como funciona o Docker?")
        self.repository.save_message(session_id, interaction_id, "assistant",
                                     "O projeto usa uma imagem Java 11.")
        self.repository.save_tool_execution(
            interaction_id, "call_1", "search_project_knowledge",
            {"query": "docker"}, {"encontrados": 2}, 14, True, None)
        self.repository.finish_interaction(interaction_id, 830, "ok")

        recentes = self.repository.recent_interactions(limit=5)
        self.assertEqual(1, len(recentes))
        self.assertEqual("como funciona o Docker?", recentes[0]["question"])
        self.assertEqual("O projeto usa uma imagem Java 11.",
                         recentes[0]["answer"])
        self.assertEqual(830, recentes[0]["elapsed_ms"])
        self.assertEqual("ok", recentes[0]["status"])

        self.assertEqual(2, self.repository.count_messages())
        self.assertEqual(1, self.repository.count_messages("user"))

        ferramentas = self.database.query(
            "SELECT tool_name, success, elapsed_ms FROM tool_executions")
        self.assertEqual(1, len(ferramentas))
        self.assertEqual("search_project_knowledge",
                         ferramentas[0]["tool_name"])
        self.assertEqual(1, ferramentas[0]["success"])
