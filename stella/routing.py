# -*- coding: utf-8 -*-
"""Roteamento determinístico para intenções Stella inequívocas."""
from __future__ import unicode_literals


DOCUMENT_MARKERS = (
    "cpf", "cnpj", "nit", "renavam", "título eleitoral", "titulo eleitoral",
    "inscrição estadual", "inscricao estadual",
)


def forced_tool_for(question):
    """Retorna a tool Stella a forçar na primeira rodada, ou ``None``.

    A função não extrai valores nem executa regras de documento; ela apenas
    evita que a LLM ignore uma intenção determinística já expressa pelo usuário.
    A própria LLM ainda constrói os argumentos conforme o schema da tool.
    """
    text = (question or "").strip().lower()
    has_document = any(marker in text for marker in DOCUMENT_MARKERS)

    if "por extenso" in text:
        return "stella_number_to_words"
    if ("capabilit" in text or "o que a stella" in text or
            ("quais documento" in text and "ger" in text)):
        return "stella_capabilities"
    if has_document and ("em lote" in text or "lote" in text):
        return "stella_validate_batch"
    if has_document and any(word in text for word in ("gere", "gerar", "gerado")):
        return "stella_generate_document"
    if has_document and any(word in text for word in (
            "formate", "formatar", "formata", "máscara", "mascara",
            "desformate", "desformatar", "remova a máscara", "remova a mascara")):
        return "stella_transform_document"
    if has_document and any(word in text for word in (
            "válido", "valido", "válida", "valida", "valide", "validar",
            "confira", "verifique")):
        return "stella_validate_document"
    return None


def tool_choice_for(name):
    """Formato OpenAI/Groq para obrigar uma function específica."""
    if not name:
        return "auto"
    return {"type": "function", "function": {"name": name}}
