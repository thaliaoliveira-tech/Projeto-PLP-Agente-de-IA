# -*- coding: utf-8 -*-
"""Bindings explícitos para os formatadores confirmados do Stella Core."""
from __future__ import unicode_literals

from stella.errors import StellaError


def create_formatter(document_type):
    from br.com.caelum.stella.format import (CPFFormatter, CNPJFormatter,
                                              NITFormatter, RenavamFormatter,
                                              TituloEleitoralFormatter)
    formatters = {
        "cpf": CPFFormatter, "cnpj": CNPJFormatter, "nit": NITFormatter,
        "renavam": RenavamFormatter, "titulo_eleitoral": TituloEleitoralFormatter,
    }
    formatter = formatters.get(document_type)
    if formatter is None:
        raise StellaError("UNSUPPORTED_OPERATION",
                          "Formatação indisponível para este documento.")
    return formatter()


def unformat(document_type, value):
    if document_type == "inscricao_estadual":
        return "".join(char for char in unicode(value) if char.isalnum())
    try:
        return unicode(create_formatter(document_type).unformat(unicode(value)))
    except Exception:
        raise StellaError("INVALID_DOCUMENT", "Valor de documento inválido.")


def transform(document_type, action, value):
    if action == "unformat":
        return unformat(document_type, value)
    if document_type == "inscricao_estadual":
        raise StellaError("UNSUPPORTED_OPERATION",
                          "A Stella não oferece máscara genérica para inscrição estadual.")
    try:
        return unicode(create_formatter(document_type).format(unformat(document_type, value)))
    except StellaError:
        raise
    except Exception:
        raise StellaError("INVALID_DOCUMENT", "Valor de documento inválido.")
