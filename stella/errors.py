# -*- coding: utf-8 -*-
from __future__ import unicode_literals


class StellaError(Exception):
    """Erro seguro do adapter; não revela detalhes da JVM ou valores privados."""
    def __init__(self, code, message):
        Exception.__init__(self, message)
        self.code = code
        self.message = message
