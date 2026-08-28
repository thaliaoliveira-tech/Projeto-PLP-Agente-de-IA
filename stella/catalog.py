# -*- coding: utf-8 -*-
"""Catálogo fechado de capabilities. Nunca recebe nomes de classes da LLM."""
from __future__ import unicode_literals

from stella.errors import StellaError


UFS = ("AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA",
       "MT", "MS", "MG", "PA", "PB", "PR", "PE", "PI", "RJ", "RN",
       "RS", "RO", "RR", "SC", "SP", "SE", "TO")

CAPABILITIES = {
    "cpf": {"validate": True, "format": True, "unformat": True,
            "generate": True, "needs_uf": False, "category": "validation"},
    "cnpj": {"validate": True, "format": True, "unformat": True,
             "generate": True, "needs_uf": False, "category": "validation"},
    "nit": {"validate": True, "format": True, "unformat": True,
            "generate": True, "needs_uf": False, "category": "validation"},
    "renavam": {"validate": True, "format": True, "unformat": True,
                "generate": True, "needs_uf": False, "category": "validation"},
    "titulo_eleitoral": {"validate": True, "format": True, "unformat": True,
                         "generate": True, "needs_uf": False,
                         "category": "validation"},
    "inscricao_estadual": {"validate": True, "format": False,
                            "unformat": True, "generate": False,
                            "needs_uf": True, "category": "validation"},
}


def normalize_document_type(document_type):
    value = (document_type or "").strip().lower().replace("-", "_").replace(" ", "_")
    aliases = {"titulo": "titulo_eleitoral", "ie": "inscricao_estadual",
               "inscricao": "inscricao_estadual"}
    value = aliases.get(value, value)
    if value not in CAPABILITIES:
        raise StellaError("UNKNOWN_DOCUMENT_TYPE", "Tipo de documento não suportado.")
    return value


def normalize_uf(uf, required=False):
    if uf is None or not unicode(uf).strip():
        if required:
            raise StellaError("UF_REQUIRED", "UF é obrigatória para inscrição estadual.")
        return None
    normalized = unicode(uf).strip().upper()
    if normalized not in UFS:
        raise StellaError("INVALID_UF", "UF inválida para inscrição estadual.")
    return normalized


def capability(document_type):
    return CAPABILITIES[normalize_document_type(document_type)]


def public_capabilities(category=None):
    wanted = (category or "all").lower()
    if wanted not in ("all", "validation", "transform", "generation"):
        raise StellaError("INVALID_CATEGORY", "Categoria de capability inválida.")
    result = []
    for name in sorted(CAPABILITIES):
        info = CAPABILITIES[name]
        if wanted == "transform" and not (info["format"] or info["unformat"]):
            continue
        if wanted == "generation" and not info["generate"]:
            continue
        result.append({"type": name, "validate": info["validate"],
                       "format": info["format"], "unformat": info["unformat"],
                       "generate": info["generate"],
                       "requires": ["uf"] if info["needs_uf"] else []})
    return result
