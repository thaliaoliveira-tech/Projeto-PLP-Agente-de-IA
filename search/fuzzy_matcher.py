# -*- coding: utf-8 -*-
"""
search/fuzzy_matcher.py -- similaridade textual usando **Apache Commons Text**,
uma biblioteca Java, chamada diretamente de dentro do código Python.

    from org.apache.commons.text.similarity import JaroWinklerSimilarity

O score final combina três sinais:

    65%  similaridade por termos (cada termo da pergunta contra os termos do
         documento, tolerando erros de digitação)
    25%  Jaro-Winkler entre a pergunta e o título/trecho de referência
    10%  Levenshtein normalizado entre a pergunta e o título/trecho

É um RAG lexical: não há embeddings nem modelo de vetor, apenas proximidade
textual calculada localmente por bibliotecas Java.

APIs Java utilizadas neste módulo:

    org.apache.commons.text.similarity.JaroWinklerSimilarity
    org.apache.commons.text.similarity.LevenshteinDistance
"""
from __future__ import unicode_literals

# Classes Java da Apache Commons Text.
from org.apache.commons.text.similarity import JaroWinklerSimilarity
from org.apache.commons.text.similarity import LevenshteinDistance

from search.normalizer import normalize, tokenize


_JARO_WINKLER = JaroWinklerSimilarity()
_LEVENSHTEIN = LevenshteinDistance()

# Pesos do score combinado.
TERM_WEIGHT = 0.65
JARO_WEIGHT = 0.25
LEVENSHTEIN_WEIGHT = 0.10

# A partir de qual similaridade dois termos são considerados "o mesmo termo"
# escrito com erro de digitação ("doker" ~ "docker").
TYPO_THRESHOLD = 0.86


def jaro_winkler(left, right):
    """Similaridade de Jaro-Winkler (0.0 a 1.0) via Apache Commons Text."""
    if not left or not right:
        return 0.0
    return float(_JARO_WINKLER.apply(left, right))


def levenshtein_ratio(left, right):
    """Distância de Levenshtein normalizada como similaridade (0.0 a 1.0)."""
    if not left or not right:
        return 0.0
    distance = int(_LEVENSHTEIN.apply(left, right))
    longest = max(len(left), len(right))
    if longest == 0:
        return 0.0
    ratio = 1.0 - (float(distance) / longest)
    return ratio if ratio > 0.0 else 0.0


def _best_token_match(term, candidates):
    """Melhor similaridade entre um termo da pergunta e os termos do documento."""
    if term in candidates:
        return 1.0
    best = 0.0
    for candidate in candidates:
        # Prefixo forte já indica a mesma palavra ("configur" em "configuracao").
        if len(term) >= 4 and (candidate.startswith(term)
                               or term.startswith(candidate)):
            return 1.0
        similarity = jaro_winkler(term, candidate)
        if similarity > best:
            best = similarity
    return best


def term_score(query_tokens, target_tokens):
    """
    Fração dos termos da pergunta encontrados no documento, tolerando erros
    de digitação.
    """
    if not query_tokens:
        return 0.0
    candidates = set(target_tokens)
    if not candidates:
        return 0.0

    total = 0.0
    for term in query_tokens:
        best = _best_token_match(term, candidates)
        if best >= 1.0:
            total += 1.0
        elif best >= TYPO_THRESHOLD:
            total += best
    return total / len(query_tokens)


def score(query, target_text, reference=None):
    """
    Score final (0.0 a 1.0) entre a pergunta e um texto.

    ``reference`` é um texto curto e representativo (título do documento,
    cabeçalho da seção ou a pergunta original registrada no histórico) usado
    nos componentes Jaro-Winkler e Levenshtein.
    """
    query_normalized = normalize(query)
    if not query_normalized:
        return 0.0

    query_tokens = tokenize(query)
    target_tokens = tokenize(target_text, keep_stopwords=True)

    terms = term_score(query_tokens, target_tokens)

    if reference is None:
        reference = target_text[:120]
    reference_normalized = normalize(reference)

    jaro = jaro_winkler(query_normalized, reference_normalized)
    levenshtein = levenshtein_ratio(query_normalized, reference_normalized)

    return (TERM_WEIGHT * terms
            + JARO_WEIGHT * jaro
            + LEVENSHTEIN_WEIGHT * levenshtein)


def rank(query, items, text_of, reference_of=None, top_k=3, min_score=0.0):
    """
    Ordena ``items`` pela proximidade com a pergunta.

    ``text_of``      -> função que devolve o texto completo de um item
    ``reference_of`` -> função que devolve o texto curto de referência
    Retorna uma lista de tuplas ``(item, score)``.
    """
    scored = []
    for item in items:
        reference = reference_of(item) if reference_of else None
        value = score(query, text_of(item), reference)
        if value >= min_score:
            scored.append((item, value))
    scored.sort(key=lambda pair: pair[1], reverse=True)
    if top_k is not None and top_k > 0:
        return scored[:top_k]
    return scored
