# -*- coding: utf-8 -*-
"""Tabela estática UF -> validator. Nenhum nome de classe vem da LLM."""
from __future__ import unicode_literals

from stella.errors import StellaError


def create_ie_validator(uf):
    from br.com.caelum.stella.validation.ie import (
        IEAcreValidator, IEAlagoasValidator, IEAmapaValidator, IEAmazonasValidator,
        IEBahiaValidator, IECearaValidator, IEDistritoFederalValidator,
        IEEspiritoSantoValidator, IEGoiasValidator, IEMaranhaoValidator,
        IEMatoGrossoValidator, IEMatoGrossoDoSulValidator, IEMinasGeraisValidator,
        IEParaValidator, IEParaibaValidator, IEParanaValidator, IEPernambucoValidator,
        IEPiauiValidator, IERioDeJaneiroValidator, IERioGrandeDoNorteValidator,
        IERioGrandeDoSulValidator, IERondoniaValidator, IERoraimaValidator,
        IESantaCatarinaValidator, IESaoPauloValidator, IESergipeValidator,
        IETocantinsValidator)
    validators = {
        "AC": IEAcreValidator, "AL": IEAlagoasValidator, "AP": IEAmapaValidator,
        "AM": IEAmazonasValidator, "BA": IEBahiaValidator, "CE": IECearaValidator,
        "DF": IEDistritoFederalValidator, "ES": IEEspiritoSantoValidator,
        "GO": IEGoiasValidator, "MA": IEMaranhaoValidator, "MT": IEMatoGrossoValidator,
        "MS": IEMatoGrossoDoSulValidator, "MG": IEMinasGeraisValidator,
        "PA": IEParaValidator, "PB": IEParaibaValidator, "PR": IEParanaValidator,
        "PE": IEPernambucoValidator, "PI": IEPiauiValidator,
        "RJ": IERioDeJaneiroValidator, "RN": IERioGrandeDoNorteValidator,
        "RS": IERioGrandeDoSulValidator, "RO": IERondoniaValidator,
        "RR": IERoraimaValidator, "SC": IESantaCatarinaValidator,
        "SP": IESaoPauloValidator, "SE": IESergipeValidator, "TO": IETocantinsValidator,
    }
    validator = validators.get(uf)
    if validator is None:
        raise StellaError("INVALID_UF", "UF inválida para inscrição estadual.")
    return validator()
