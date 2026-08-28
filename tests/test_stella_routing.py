# -*- coding: utf-8 -*-
"""Roteamento das perguntas naturais para a tool Stella obrigatória."""
from __future__ import unicode_literals

import unittest

import json

from groq_client import GroqClient
from stella.routing import forced_tool_for, tool_choice_for


class StellaRoutingTest(unittest.TestCase):

    def test_routes_document_intents(self):
        self.assertEqual("stella_validate_document",
                         forced_tool_for("O CPF 529.982.247-25 é válido?"))
        self.assertEqual("stella_transform_document",
                         forced_tool_for("Formate o CPF 52998224725."))
        self.assertEqual("stella_generate_document",
                         forced_tool_for("Gere um CNPJ válido para teste."))
        self.assertEqual("stella_validate_batch",
                         forced_tool_for("Valide estes CPFs em lote."))

    def test_routes_non_document_capabilities_and_words(self):
        self.assertEqual("stella_number_to_words",
                         forced_tool_for("Escreva 123 por extenso."))
        self.assertEqual("stella_capabilities",
                         forced_tool_for("Quais capabilities a Stella possui?"))
        self.assertIsNone(forced_tool_for("Explique o que é Jython."))

    def test_forced_choice_has_groq_shape(self):
        choice = tool_choice_for("stella_validate_document")
        self.assertEqual("function", choice["type"])
        self.assertEqual("stella_validate_document", choice["function"]["name"])
        self.assertEqual("auto", tool_choice_for(None))

        client = GroqClient(api_key="chave-de-teste")
        payload = json.loads(client._build_payload(
            [{"role": "user", "content": "O CPF é válido?"}],
            [{"type": "function", "function": {
                "name": "stella_validate_document", "description": "teste",
                "parameters": {"type": "object", "properties": {}}}}],
            choice))
        self.assertEqual(choice, payload["tool_choice"])
