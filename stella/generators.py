# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from stella.errors import StellaError
from stella.validators import create_validator
from stella.formatters import transform


def generate(document_type, formatted=False):
    try:
        value = unicode(create_validator(document_type).generateRandomValid())
    except Exception:
        raise StellaError("UNSUPPORTED_OPERATION",
                          "Geração indisponível para este documento.")
    return transform(document_type, "format", value) if formatted else value
