# -*- coding: utf-8 -*-
"""
tests/test_groq_client.py -- configuração, payload e tool_calls (T01, T05,
T06) e o teste de integração real (T90).
"""
from __future__ import unicode_literals

import json
import unittest

import config
from groq_client import GroqClient, GroqError


class ConfigurationTest(unittest.TestCase):

    # T01 -----------------------------------------------------------------
    def test_default_model(self):
        self.assertEqual("openai/gpt-oss-120b", config.DEFAULT_MODEL)
        self.assertEqual("https://api.groq.com/openai/v1/chat/completions",
                         config.DEFAULT_API_URL)

        cliente = GroqClient(api_key="chave-de-teste")
        self.assertEqual(config.GROQ_MODEL, cliente.model)
        self.assertEqual(config.GROQ_API_URL, cliente.api_url)
        self.assertTrue(config.AGENT_MAX_ITERATIONS >= 1)


class PayloadTest(unittest.TestCase):

    def setUp(self):
        self.client = GroqClient(api_key="chave-de-teste",
                                 model="openai/gpt-oss-120b")
        self.tools = [{
            "type": "function",
            "function": {
                "name": "search_project_knowledge",
                "description": "pesquisa a documentação",
                "parameters": {"type": "object",
                               "properties": {"query": {"type": "string"}},
                               "required": ["query"]},
            },
        }]

    # T05 -----------------------------------------------------------------
    def test_payload_includes_tools(self):
        mensagens = [{"role": "user", "content": "como funciona o Docker?"}]
        corpo = json.loads(self.client._build_payload(mensagens, self.tools))

        self.assertEqual("openai/gpt-oss-120b", corpo["model"])
        self.assertEqual("auto", corpo["tool_choice"])
        self.assertEqual(1, len(corpo["tools"]))
        self.assertEqual("search_project_knowledge",
                         corpo["tools"][0]["function"]["name"])
        self.assertFalse(corpo["stream"])

        # Sem ferramentas, o payload não carrega os campos de tool calling.
        simples = json.loads(self.client._build_payload(mensagens))
        self.assertNotIn("tools", simples)
        self.assertNotIn("tool_choice", simples)

    # T06 -----------------------------------------------------------------
    def test_parse_tool_calls(self):
        resposta = json.dumps({
            "model": "openai/gpt-oss-120b",
            "choices": [{
                "index": 0,
                "finish_reason": "tool_calls",
                "message": {
                    "role": "assistant",
                    "content": None,
                    "reasoning": "O usuário quer saber sobre Docker; vou "
                                 "consultar a base de conhecimento.",
                    "tool_calls": [{
                        "id": "call_abc123",
                        "type": "function",
                        "function": {
                            "name": "search_project_knowledge",
                            "arguments": "{\"query\": \"docker\", \"limit\": 2}",
                        },
                    }],
                },
            }],
            "usage": {"prompt_tokens": 120, "completion_tokens": 18,
                      "total_tokens": 138,
                      "prompt_tokens_details": {"cached_tokens": 64}},
        })

        reply = self.client._parse_reply(resposta, 250)

        self.assertTrue(reply.has_tool_calls)
        self.assertIsNone(reply.content)
        self.assertEqual("tool_calls", reply.finish_reason)
        self.assertEqual(1, len(reply.tool_calls))

        chamada = reply.tool_calls[0]
        self.assertEqual("call_abc123", chamada.id)
        self.assertEqual("search_project_knowledge", chamada.name)
        self.assertEqual("docker", chamada.arguments["query"])
        self.assertEqual(2, chamada.arguments["limit"])

        # O raciocínio precisa ser preservado: ele volta ao histórico junto com
        # o pedido de ferramenta, senão o modelo degenera em rodadas seguintes.
        self.assertTrue(reply.reasoning)
        self.assertIn("base de conhecimento", reply.reasoning)

        self.assertEqual(64, reply.cached_tokens)
        self.assertEqual(138, reply.total_tokens)
        self.assertEqual(250, reply.elapsed_ms)

        # O formato de reenvio no histórico precisa ser aceito pela API.
        parte = chamada.to_message_part()
        self.assertEqual("function", parte["type"])
        self.assertEqual("search_project_knowledge", parte["function"]["name"])


class GroqIntegrationTest(unittest.TestCase):
    """T90 -- chama a Groq de verdade. Não roda na execução padrão."""

    # T90 -----------------------------------------------------------------
    def test_real_request(self):
        if not config.GROQ_API_KEY:
            self.fail("GROQ_API_KEY não configurada: o teste de integração "
                      "precisa de uma chave válida.")

        cliente = GroqClient()
        try:
            reply = cliente.ask("Responda apenas com a palavra: pronto.")
        except GroqError as error:
            self.fail("A chamada real à Groq falhou: %s" % error.message)

        self.assertTrue(reply.content)
        self.assertTrue(reply.total_tokens > 0)
        self.assertEqual(config.GROQ_MODEL.split("/")[-1],
                         reply.model.split("/")[-1])
