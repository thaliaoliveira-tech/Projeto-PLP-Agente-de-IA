# -*- coding: utf-8 -*-
"""tests/test_chat.py -- histórico da conversa (T02, T03, T04)."""
from __future__ import unicode_literals

import unittest

from chat import ChatSession, ROLE_SYSTEM, ROLE_USER, ROLE_ASSISTANT, ROLE_TOOL
from groq_client import ToolCall


class ChatSessionTest(unittest.TestCase):

    def setUp(self):
        self.session = ChatSession("prompt de sistema para teste")

    # T02 -----------------------------------------------------------------
    def test_history_is_java_arraylist(self):
        self.assertEqual("java.util.ArrayList", self.session.backing_class())

        self.session.add_user("mensagem")
        primeira = self.session.history.get(0)
        self.assertEqual("java.util.LinkedHashMap",
                         primeira.getClass().getName())

    # T03 -----------------------------------------------------------------
    def test_add_user_and_assistant(self):
        self.session.add_user("meu nome é João")
        self.session.add_assistant("Prazer, João!")

        mensagens = self.session.messages()
        self.assertEqual(3, len(mensagens))
        self.assertEqual(ROLE_SYSTEM, mensagens[0]["role"])
        self.assertEqual(ROLE_USER, mensagens[1]["role"])
        self.assertEqual("meu nome é João", mensagens[1]["content"])
        self.assertEqual(ROLE_ASSISTANT, mensagens[2]["role"])
        self.assertEqual(2, self.session.exchanged_messages())

    # T04 -----------------------------------------------------------------
    def test_clear_keeps_system_prompt(self):
        self.session.add_user("primeira")
        self.session.add_assistant("resposta")
        self.assertEqual(3, self.session.size())

        self.session.clear()

        self.assertEqual(1, self.session.size())
        self.assertTrue(self.session.is_empty())
        mensagens = self.session.messages()
        self.assertEqual(ROLE_SYSTEM, mensagens[0]["role"])
        self.assertEqual("prompt de sistema para teste",
                         mensagens[0]["content"])

    # T15 -----------------------------------------------------------------
    def test_context_window(self):
        def rodada(numero, com_ferramenta=False):
            self.session.add_user("pergunta %d" % numero)
            if com_ferramenta:
                chamada = ToolCall("call_%d" % numero, "list_project_tests", {})
                self.session.add_assistant_tool_calls(None, [chamada])
                self.session.add_tool_result("call_%d" % numero,
                                             "list_project_tests", "{}")
            self.session.add_assistant("resposta %d" % numero)

        for numero in range(4):
            rodada(numero, com_ferramenta=(numero % 2 == 0))

        self.assertEqual(4, self.session.turns())

        # A janela descarta as rodadas mais antigas...
        descartadas = self.session.trim_to_turns(2)
        self.assertTrue(descartadas > 0)
        self.assertEqual(2, self.session.turns())

        # ...preservando o prompt de sistema e cortando antes de um "user".
        mensagens = self.session.messages()
        self.assertEqual(ROLE_SYSTEM, mensagens[0]["role"])
        self.assertEqual(ROLE_USER, mensagens[1]["role"])
        self.assertEqual("pergunta 2", mensagens[1]["content"])

        # Nenhum resultado de ferramenta pode ficar órfão: a API rejeita uma
        # mensagem "tool" sem o tool_call correspondente antes dela.
        pendentes = 0
        for mensagem in mensagens:
            if mensagem["role"] == ROLE_ASSISTANT and mensagem.get("tool_calls"):
                pendentes += len(mensagem["tool_calls"])
            elif mensagem["role"] == ROLE_TOOL:
                pendentes -= 1
            self.assertTrue(pendentes >= 0,
                            "resultado de ferramenta sem o pedido correspondente")
        self.assertEqual(0, pendentes)

        # Uma janela maior que o histórico não mexe em nada.
        tamanho = self.session.size()
        self.assertEqual(0, self.session.trim_to_turns(10))
        self.assertEqual(tamanho, self.session.size())
