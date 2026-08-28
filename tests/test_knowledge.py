# -*- coding: utf-8 -*-
"""
tests/test_knowledge.py -- busca fuzzy na base de conhecimento (T08, T09, T10).

Os testes usam a base real do projeto, em ``knowledge/``, e comprovam que a
similaridade textual do Apache Commons Text encontra o documento certo mesmo
quando a pergunta tem erros de digitação.
"""
from __future__ import unicode_literals

import unittest

from tools.knowledge_tool import KnowledgeBase


class FuzzySearchTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.knowledge = KnowledgeBase()
        cls.knowledge.load()

    def _documentos(self, resultados):
        return [item["documento"] for item in resultados]

    # T08 -----------------------------------------------------------------
    def test_exact_match(self):
        self.assertTrue(self.knowledge.document_count() >= 8,
                        "a base de conhecimento deveria ter 8 documentos")

        resultados = self.knowledge.search(
            "como configuro o docker para rodar o jython?", top_k=3)

        self.assertTrue(len(resultados) > 0, "nenhum trecho foi encontrado")
        self.assertEqual("08_docker_configuration.md",
                         resultados[0]["documento"])
        self.assertTrue(resultados[0]["score"] > 0.4)

        # Uma pergunta sobre banco de dados encontra o documento de banco.
        banco = self.knowledge.search(
            "quais tabelas existem no banco de dados sqlite?", top_k=3)
        self.assertIn("07_database_metrics.md", self._documentos(banco))

    # T09 -----------------------------------------------------------------
    def test_typo_match(self):
        resultados = self.knowledge.search(
            "como confguro o doker pra roda jyton?", top_k=3)

        self.assertTrue(len(resultados) > 0,
                        "a busca com erros de digitação não achou nada")
        self.assertEqual("08_docker_configuration.md",
                         resultados[0]["documento"])
        self.assertTrue(
            resultados[0]["score"] > 0.35,
            "score baixo demais: %s" % resultados[0]["score"])

    # T10 -----------------------------------------------------------------
    def test_top_k_limit(self):
        for limite in (1, 2, 3, 5):
            resultados = self.knowledge.search("jython java jvm docker groq",
                                               top_k=limite)
            self.assertTrue(
                len(resultados) <= limite,
                "top_k=%d devolveu %d resultados" % (limite, len(resultados)))

        # Cada trecho respeita o limite de caracteres.
        resultados = self.knowledge.search("jython", top_k=3, max_chars=200)
        for item in resultados:
            self.assertTrue(len(item["trecho"]) <= 200)
