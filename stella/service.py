# -*- coding: utf-8 -*-
"""Fachada estável entre tools Python e a API Java Caelum Stella."""
from __future__ import unicode_literals

import config
from stella import catalog
from stella.errors import StellaError
from stella import validators, formatters, generators, inwords


class StellaService(object):
    def __init__(self, batch_max_items=None, input_max_length=None):
        self.batch_max_items = (batch_max_items if batch_max_items is not None
                                else config.STELLA_BATCH_MAX_ITEMS)
        self.input_max_length = (input_max_length if input_max_length is not None
                                 else config.STELLA_INPUT_MAX_LENGTH)

    def smoke_test(self):
        """Confirma, no bootstrap, que o Jython enxerga o JAR no classpath."""
        validators.create_validator("cpf")
        return True

    def capabilities(self, category=None):
        return {"capabilities": catalog.public_capabilities(category),
                "batch_max_items": self.batch_max_items}

    def validate(self, document_type, value, uf=None, formatted=None, details=True):
        doc_type = catalog.normalize_document_type(document_type)
        info = catalog.capability(doc_type)
        state = catalog.normalize_uf(uf, info["needs_uf"])
        self._check_value(value)
        normalized = formatters.unformat(doc_type, value)
        validator = validators.create_validator(doc_type, state)
        valid = validators.is_valid(validator, normalized)
        result = {"operation": "validate", "document_type": doc_type,
                  "valid": valid, "normalized": normalized,
                  "errors": [] if valid else [{"code": "INVALID_DOCUMENT",
                                                 "message": "Documento inválido."}]}
        if state:
            result["uf"] = state
        if formatted and info["format"]:
            result["formatted"] = formatters.transform(doc_type, "format", normalized)
        if not details:
            result.pop("normalized", None)
            result.pop("formatted", None)
        return result

    def transform(self, document_type, action, value):
        doc_type = catalog.normalize_document_type(document_type)
        action = (action or "").lower()
        if action not in ("format", "unformat"):
            raise StellaError("INVALID_ACTION", "Ação deve ser format ou unformat.")
        self._check_value(value)
        output = formatters.transform(doc_type, action, value)
        return {"document_type": doc_type, "action": action,
                "input": unicode(value), "output": output}

    def generate(self, document_type, formatted=True):
        doc_type = catalog.normalize_document_type(document_type)
        if not catalog.capability(doc_type)["generate"]:
            raise StellaError("UNSUPPORTED_OPERATION",
                              "Geração indisponível para este documento.")
        value = generators.generate(doc_type, formatted)
        return {"document_type": doc_type, "value": value, "valid": True}

    def number_to_words(self, value):
        return {"operation": "number_to_words", "input": value,
                "output": inwords.number_to_words(value)}

    def validate_batch(self, document_type, values, uf=None, formatted=None,
                       details=False):
        if not isinstance(values, (list, tuple)):
            raise StellaError("INVALID_BATCH", "values deve ser uma lista.")
        if not values or len(values) > self.batch_max_items:
            raise StellaError("BATCH_LIMIT", "O lote deve ter entre 1 e %d itens."
                              % self.batch_max_items)
        results = [self.validate(document_type, value, uf, formatted, details)
                   for value in values]
        invalid_items = [{"index": index, "reason": "Documento inválido."}
                         for index, result in enumerate(results)
                         if not result["valid"]]
        response = {"operation": "validate_batch", "document_type":
                    catalog.normalize_document_type(document_type),
                    "total": len(results),
                    "valid": len(results) - len(invalid_items),
                    "invalid": len(invalid_items), "invalid_items": invalid_items}
        if details:
            response["results"] = results
        return response

    def _check_value(self, value):
        if value is None or not unicode(value).strip():
            raise StellaError("INVALID_DOCUMENT", "Valor de documento ausente.")
        if len(unicode(value)) > self.input_max_length:
            raise StellaError("INPUT_TOO_LONG", "Valor de documento excede o limite.")
