# -*- coding: utf-8 -*-
"""
search/normalizer.py -- normalização de texto para a busca fuzzy.

A remoção de acentos é feita com ``java.text.Normalizer``, a API padrão da
plataforma Java para normalização Unicode: o texto é decomposto na forma NFD
(cada letra acentuada vira letra + marca de acento) e as marcas combinantes
são descartadas.

    "configuração"  ->  NFD  ->  "configurac~ao"  ->  "configuracao"

APIs Java utilizadas neste módulo:

    java.text.Normalizer -> normalização Unicode (NFD)
"""
from __future__ import unicode_literals

import re

# Classe Java responsável pela normalização Unicode.
from java.text import Normalizer


# Marcas diacríticas combinantes (acentos) deixadas pela decomposição NFD.
_COMBINING = re.compile("[\u0300-\u036f]")

# Tudo que não for letra ou dígito vira separador.
_NON_WORD = re.compile("[^0-9a-z]+")

# Palavras muito comuns em português que não ajudam no ranqueamento.
STOPWORDS = frozenset([
    "a", "ao", "aos", "as", "com", "como", "da", "das", "de", "do", "dos",
    "e", "em", "essa", "esse", "esta", "este", "eu", "ha", "isso", "ja",
    "la", "mais", "mas", "me", "meu", "minha", "muito", "na", "nas", "no",
    "nos", "num", "numa", "o", "os", "ou", "para", "pela", "pelo", "por",
    "pra", "pro", "que", "qual", "quais", "quando", "se", "sem", "ser",
    "seu", "sua", "tem", "um", "uma", "voce", "vc", "sobre", "qu",
])

MIN_TOKEN_LENGTH = 2


def strip_accents(text):
    """Remove acentos usando ``java.text.Normalizer`` (forma NFD)."""
    if text is None:
        return ""
    decomposed = Normalizer.normalize(text, Normalizer.Form.NFD)
    return _COMBINING.sub("", decomposed)


def normalize(text):
    """Deixa o texto em minúsculas, sem acentos e sem pontuação."""
    if text is None:
        return ""
    lowered = strip_accents(text).lower()
    return _NON_WORD.sub(" ", lowered).strip()


def tokenize(text, keep_stopwords=False):
    """Converte o texto em uma lista de termos normalizados."""
    tokens = []
    for token in normalize(text).split(" "):
        if not token or len(token) < MIN_TOKEN_LENGTH:
            continue
        if not keep_stopwords and token in STOPWORDS:
            continue
        tokens.append(token)
    return tokens
