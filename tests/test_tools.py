# -*- coding: utf-8 -*-
"""tests/test_tools.py -- registro e lista branca de ferramentas (T07)."""
from __future__ import unicode_literals

import unittest

from tools.registry import Tool, ToolRegistry, ToolError, WHITELIST


class RegistryTest(unittest.TestCase):

    def setUp(self):
        self.registry = ToolRegistry()
        self.registry.register(Tool(
            name="list_project_tests",
            description="ferramenta de teste",
            parameters={"target": {"type": "string"}},
            required=[],
            handler=lambda target=None: {"ok": True, "target": target},
        ))

    # T07 -----------------------------------------------------------------
    def test_whitelist(self):
        # Uma ferramenta válida é encontrada e executada.
        self.assertTrue(self.registry.has("list_project_tests"))
        resultado = self.registry.execute("list_project_tests", {})
        self.assertTrue(resultado.success)
        self.assertTrue(resultado.result["ok"])

        # Um nome desconhecido não executa nada e devolve erro controlado.
        negado = self.registry.execute("delete_everything", {})
        self.assertFalse(negado.success)
        self.assertIn("inexistente", negado.result["error"])

        # Registrar fora da lista branca é proibido.
        proibida = Tool("delete_everything", "perigosa", {}, lambda: {})
        self.assertRaises(ToolError, self.registry.register, proibida)

        # O schema enviado à Groq tem o formato esperado.
        schema = self.registry.schemas()[0]
        self.assertEqual("function", schema["type"])
        self.assertEqual("list_project_tests", schema["function"]["name"])
        self.assertIn("list_project_tests", WHITELIST)
