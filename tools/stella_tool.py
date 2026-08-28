# -*- coding: utf-8 -*-
"""Gateway compacto de tool calling para capabilities do Caelum Stella."""
from __future__ import unicode_literals

from stella.errors import StellaError
from stella.privacy import SENSITIVE_FIELDS
from tools.registry import Tool, ToolError


DOCUMENT_TYPES = ["cpf", "cnpj", "nit", "renavam", "titulo_eleitoral",
                  "inscricao_estadual"]
UFS = ["AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA",
       "MT", "MS", "MG", "PA", "PB", "PR", "PE", "PI", "RJ", "RN",
       "RS", "RO", "RR", "SC", "SP", "SE", "TO"]


def create_tools(context):
    service = context.stella

    def invoke(method, *args, **kwargs):
        if service is None:
            raise ToolError("Caelum Stella não foi inicializada no runtime.")
        try:
            return getattr(service, method)(*args, **kwargs)
        except StellaError as error:
            raise ToolError(error.message)

    def validate_document(document_type, value, uf=None, formatted=False,
                          details=True):
        return invoke("validate", document_type, value, uf, formatted, details)

    def transform_document(document_type, action, value):
        return invoke("transform", document_type, action, value)

    def generate_document(document_type, formatted=True):
        return invoke("generate", document_type, formatted)

    def number_to_words(value):
        return invoke("number_to_words", value)

    def capabilities(category=None):
        return invoke("capabilities", category)

    def validate_batch(document_type, values, uf=None, formatted=False,
                       details=False):
        return invoke("validate_batch", document_type, values, uf, formatted,
                      details)

    document = {"type": "string", "enum": DOCUMENT_TYPES}
    uf = {"type": "string", "minLength": 2, "maxLength": 2}
    value = {"type": "string", "minLength": 1, "maxLength": 64}
    batch_max = service.batch_max_items if service is not None else 100
    sensitive = list(SENSITIVE_FIELDS)
    redact = "redact"
    return [
        Tool("stella_validate_document",
             "Valida CPF, CNPJ, NIT, RENAVAM, título eleitoral ou inscrição "
             "estadual localmente com Caelum Stella. Para inscrição estadual, "
             "informe a UF.",
             {"document_type": document, "value": value, "uf": uf,
              "formatted": {"type": "boolean"}, "details": {"type": "boolean"}},
             validate_document, ["document_type", "value"], sensitive,
             "stella", redact),
        Tool("stella_transform_document",
             "Formata ou remove a máscara de documentos suportados pela Caelum "
             "Stella. Não use para validar documentos.",
             {"document_type": document, "action": {"type": "string",
              "enum": ["format", "unformat"]}, "value": value},
             transform_document, ["document_type", "action", "value"], sensitive,
             "stella", redact),
        Tool("stella_generate_document",
             "Gera localmente um documento válido somente quando essa capability "
             "é oferecida pela Caelum Stella.",
             {"document_type": document, "formatted": {"type": "boolean"}},
             generate_document, ["document_type"], sensitive, "stella", redact),
        Tool("stella_number_to_words",
             "Converte um número para palavras usando a Caelum Stella.",
             {"value": {"type": "number", "minimum": -999999999999,
                        "maximum": 999999999999}},
             number_to_words, ["value"], [], "stella"),
        Tool("stella_capabilities",
             "Lista de forma compacta os documentos e operações disponíveis na "
             "integração Caelum Stella.",
             {"category": {"type": "string", "enum": ["all", "validation",
                           "transform", "generation"]}},
             capabilities, [], [], "stella"),
        Tool("stella_validate_batch",
             "Valida em lote até o limite configurado de documentos do mesmo tipo. "
             "Por padrão devolve somente um resumo para evitar resultados extensos.",
             {"document_type": document,
              "values": {"type": "array", "items": value, "minItems": 1,
                         "maxItems": batch_max}, "uf": uf,
              "formatted": {"type": "boolean"}, "details": {"type": "boolean"}},
             validate_batch, ["document_type", "values"], sensitive, "stella", redact),
    ]
