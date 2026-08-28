# -*- coding: utf-8 -*-
"""
Pacote ``search`` -- busca textual/fuzzy local (RAG lexical, sem embeddings).

    normalizer.py    -> normalização de texto com java.text.Normalizer
    chunker.py       -> quebra dos Markdown em trechos pequenos
    fuzzy_matcher.py -> similaridade com Apache Commons Text (biblioteca Java)
"""
from __future__ import unicode_literals

from search.normalizer import normalize, tokenize, strip_accents
from search.chunker import Chunk, chunk_markdown, chunk_text
from search.fuzzy_matcher import (score, jaro_winkler, levenshtein_ratio,
                                  term_score, rank)

__all__ = [
    "normalize", "tokenize", "strip_accents",
    "Chunk", "chunk_markdown", "chunk_text",
    "score", "jaro_winkler", "levenshtein_ratio", "term_score", "rank",
]
