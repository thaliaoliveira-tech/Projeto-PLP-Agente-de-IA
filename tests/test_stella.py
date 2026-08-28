# -*- coding: utf-8 -*-
"""Testes offline do adapter Caelum Stella (executados no Jython)."""
from __future__ import unicode_literals

import json
import unittest

from java.io import File
from java.lang import System
from java.util import UUID

from database.connection import Database
from database.interaction_repository import InteractionRepository
from stella.service import StellaService
from stella.privacy import SENSITIVE_FIELDS
from tools.registry import Tool, ToolRegistry


class StellaServiceTest(unittest.TestCase):

    def setUp(self):
        self.stella = StellaService(batch_max_items=3)

    def test_cpf_cnpj_transform_and_catalog(self):
        cpf = self.stella.validate("cpf", "529.982.247-25", formatted=True)
        self.assertTrue(cpf["valid"])
        self.assertEqual("52998224725", cpf["normalized"])
        self.assertEqual("529.982.247-25", cpf["formatted"])

        cnpj = self.stella.validate("cnpj", "04.252.011/0001-10")
        self.assertTrue(cnpj["valid"])
        self.assertEqual("04.252.011/0001-10",
                         self.stella.transform("cnpj", "format", "04252011000110")["output"])
        types = [item["type"] for item in self.stella.capabilities()["capabilities"]]
        self.assertIn("inscricao_estadual", types)

    def test_generated_documents_validate(self):
        for document_type in ("cpf", "cnpj", "nit", "renavam", "titulo_eleitoral"):
            generated = self.stella.generate(document_type, formatted=False)
            self.assertTrue(self.stella.validate(document_type, generated["value"])["valid"])

    def test_batch_limit_and_summary(self):
        result = self.stella.validate_batch(
            "cpf", ["52998224725", "11111111111"], details=False)
        self.assertEqual(2, result["total"])
        self.assertEqual(1, result["valid"])
        self.assertNotIn("results", result)
        self.assertRaises(Exception, self.stella.validate_batch, "cpf",
                          ["1", "2", "3", "4"])

    def test_ie_requires_uf_and_number_to_words_uses_java_core(self):
        self.assertRaises(Exception, self.stella.validate,
                          "inscricao_estadual", "110.042.490.114")
        ie = self.stella.validate("inscricao_estadual", "110.042.490.114", "SP")
        self.assertEqual("SP", ie["uf"])
        self.assertEqual("inscricao_estadual", ie["document_type"])
        words = self.stella.number_to_words(123)
        self.assertTrue(words["output"])


class StellaPrivacyTest(unittest.TestCase):

    def test_sensitive_document_is_not_present_in_audit_copy(self):
        raw = "529.982.247-25"
        registry = ToolRegistry()
        registry.register(Tool(
            "stella_validate_document", "teste", {"value": {"type": "string"}},
            lambda value: {"normalized": "52998224725", "valid": True}, ["value"],
            list(SENSITIVE_FIELDS), "stella", "redact"))
        result = registry.execute("stella_validate_document", {"value": raw})
        self.assertEqual(raw, result.arguments["value"])
        audited = json.dumps({"arguments": result.audit_arguments,
                              "result": result.audit_result})
        self.assertNotIn(raw, audited)
        self.assertNotIn("52998224725", audited)

    def test_raw_document_never_reaches_tool_executions(self):
        raw = "529.982.247-25"
        path = "%s%sstella-privacy-%s.db" % (
            System.getProperty("java.io.tmpdir"), File.separator,
            UUID.randomUUID().toString())
        database = Database(path).connect()
        try:
            repository = InteractionRepository(database)
            session = repository.start_session("test", "2.7", "11")
            interaction = repository.start_interaction(session)
            registry = ToolRegistry()
            registry.register(Tool(
                "stella_validate_document", "teste", {"value": {"type": "string"}},
                lambda value: {"normalized": "52998224725", "valid": True}, ["value"],
                list(SENSITIVE_FIELDS), "stella", "redact"))
            result = registry.execute("stella_validate_document", {"value": raw})
            repository.save_tool_execution(
                interaction, "call_privacy", result.name, result.audit_arguments,
                result.audit_result, result.elapsed_ms, result.success, result.error)
            stored = database.query(
                "SELECT arguments_json, result_json FROM tool_executions")[0]
            self.assertNotIn(raw, stored["arguments_json"] + stored["result_json"])
            self.assertNotIn("52998224725",
                             stored["arguments_json"] + stored["result_json"])
        finally:
            database.close()
            file_object = File(path)
            if file_object.exists():
                file_object.delete()
