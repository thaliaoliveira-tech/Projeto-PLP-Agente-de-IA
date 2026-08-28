# -*- coding: utf-8 -*-
"""
search/chunker.py -- quebra dos documentos Markdown em trechos pequenos.

A base de conhecimento nunca é enviada inteira para a LLM. Cada arquivo de
``knowledge/`` é dividido em trechos ("chunks") de 500 a 1.000 caracteres,
delimitados pelos títulos do Markdown. Só os trechos mais relevantes para a
pergunta chegam ao modelo, o que reduz tokens, custo e latência.
"""
from __future__ import unicode_literals

import re


DEFAULT_MAX_CHARS = 1000
DEFAULT_MIN_CHARS = 500

_HEADING = re.compile(r"^(#{1,6})\s+(.*)$")


class Chunk(object):
    """Um trecho recuperável da base de conhecimento."""

    def __init__(self, doc_id, title, heading, text, index=0):
        self.doc_id = doc_id
        self.title = title
        self.heading = heading
        self.text = text
        self.index = index

    @property
    def label(self):
        if self.heading and self.heading != self.title:
            return "%s > %s" % (self.title, self.heading)
        return self.title

    def search_text(self):
        """Texto usado no ranqueamento (inclui os títulos)."""
        return "%s %s %s" % (self.title, self.heading, self.text)

    def to_dict(self):
        return {
            "doc_id": self.doc_id,
            "title": self.title,
            "heading": self.heading,
            "text": self.text,
            "index": self.index,
        }

    def __repr__(self):
        return "<Chunk %s#%d %s>" % (self.doc_id, self.index, self.heading)


def _split_long(text, max_chars):
    """Divide um bloco grande em pedaços, respeitando parágrafos."""
    if len(text) <= max_chars:
        return [text]

    pieces = []
    current = []
    size = 0
    for paragraph in text.split("\n\n"):
        piece_len = len(paragraph) + 2
        if size + piece_len > max_chars and current:
            pieces.append("\n\n".join(current).strip())
            current = []
            size = 0
        current.append(paragraph)
        size += piece_len
    if current:
        pieces.append("\n\n".join(current).strip())

    # Um parágrafo isolado ainda pode passar do limite: corta no cru.
    final = []
    for piece in pieces:
        while len(piece) > max_chars:
            final.append(piece[:max_chars])
            piece = piece[max_chars:]
        if piece.strip():
            final.append(piece.strip())
    return final


def chunk_text(doc_id, content, max_chars=DEFAULT_MAX_CHARS,
               min_chars=DEFAULT_MIN_CHARS):
    """Divide o conteúdo de um Markdown em uma lista de ``Chunk``."""
    title = doc_id
    heading = doc_id
    buffer = []
    blocks = []

    def flush():
        text = "\n".join(buffer).strip()
        if text:
            blocks.append((heading, text))
        del buffer[:]

    for line in content.splitlines():
        match = _HEADING.match(line)
        if match:
            level = len(match.group(1))
            text = match.group(2).strip()
            if level == 1:
                flush()
                title = text
                heading = text
            else:
                flush()
                heading = text
            continue
        buffer.append(line)
    flush()

    # Junta blocos curtos consecutivos até atingir o tamanho mínimo.
    merged = []
    for block_heading, text in blocks:
        if merged and len(merged[-1][1]) < min_chars \
                and len(merged[-1][1]) + len(text) <= max_chars:
            previous_heading, previous_text = merged[-1]
            merged[-1] = (previous_heading, previous_text + "\n\n" + text)
        else:
            merged.append((block_heading, text))

    chunks = []
    index = 0
    for block_heading, text in merged:
        for piece in _split_long(text, max_chars):
            chunks.append(Chunk(doc_id, title, block_heading, piece, index))
            index += 1
    return chunks


def chunk_markdown(doc_id, content, **kwargs):
    """Alias explícito de ``chunk_text`` para arquivos Markdown."""
    return chunk_text(doc_id, content, **kwargs)
