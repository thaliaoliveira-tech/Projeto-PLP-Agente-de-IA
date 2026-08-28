# -*- coding: utf-8 -*-
"""Bindings explícitos de validators Stella; não há reflexão dinâmica."""
from __future__ import unicode_literals

from stella.errors import StellaError


def create_validator(document_type, uf=None):
    from br.com.caelum.stella.validation import (CPFValidator, CNPJValidator,
                                                  NITValidator, RenavamValidator,
                                                  TituloEleitoralValidator)
    validators = {
        "cpf": CPFValidator, "cnpj": CNPJValidator, "nit": NITValidator,
        "renavam": RenavamValidator, "titulo_eleitoral": TituloEleitoralValidator,
    }
    if document_type == "inscricao_estadual":
        from stella.ie import create_ie_validator
        return create_ie_validator(uf)
    validator = validators.get(document_type)
    if validator is None:
        raise StellaError("UNSUPPORTED_OPERATION", "Validação indisponível.")
    return validator()


def is_valid(validator, value):
    from java.lang import Throwable
    try:
        validator.assertValid(value)
        return True
    except Throwable:
        return False
    except Exception:
        return False
