# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from stella.errors import StellaError


def number_to_words(value):
    try:
        from br.com.caelum.stella.inwords import (NumericToWordsConverter,
                                                   FormatoDeInteiro,
                                                   FormatoDeReal)
        number = float(value)
        integer = number == int(number)
        converter = NumericToWordsConverter(
            FormatoDeInteiro() if integer else FormatoDeReal())
        numeric = int(number) if integer else number
        return unicode(converter.toWords(numeric))
    except Exception:
        raise StellaError("INVALID_NUMBER", "Número inválido para conversão por extenso.")
