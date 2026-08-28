# -*- coding: utf-8 -*-
"""
tests/registry.py -- catálogo e executor da suíte de testes.

Cada teste automatizado recebe um identificador legível (T01, T02, ...), o que
permite ao próprio agente listar e executar testes selecionados pelo
identificador, por palavra-chave ou todos de uma vez.

Os quinze testes T01 a T15 são **offline**: não gastam tokens da Groq e usam
bancos temporários. O T90 é o único que chama a API de verdade e nunca entra
na execução padrão.

APIs Java utilizadas neste módulo:

    java.lang.System.currentTimeMillis() -> tempo total da execução
"""
from __future__ import unicode_literals

import unittest
from StringIO import StringIO

from java.lang import System


# ---------------------------------------------------------------------------
# Catálogo
# ---------------------------------------------------------------------------
TESTS = [
    {"id": "T01",
     "name": "Configuração padrão do modelo",
     "description": "O modelo padrão é openai/gpt-oss-120b e o endpoint é o "
                    "de chat completions da Groq.",
     "module": "tests.test_groq_client", "class": "ConfigurationTest",
     "method": "test_default_model", "tags": ["config", "configuracao", "groq"],
     "offline": True},

    {"id": "T02",
     "name": "Histórico usa java.util.ArrayList",
     "description": "O histórico da conversa é sustentado por uma coleção "
                    "Java, não por uma lista Python.",
     "module": "tests.test_chat", "class": "ChatSessionTest",
     "method": "test_history_is_java_arraylist",
     "tags": ["chat", "java", "historico", "arraylist"], "offline": True},

    {"id": "T03",
     "name": "Adição de mensagens user/assistant",
     "description": "Mensagens de usuário e de assistente entram no histórico "
                    "na ordem correta.",
     "module": "tests.test_chat", "class": "ChatSessionTest",
     "method": "test_add_user_and_assistant",
     "tags": ["chat", "historico"], "offline": True},

    {"id": "T04",
     "name": "Limpeza do contexto preserva o system prompt",
     "description": "O comando /clear esvazia o ArrayList e reinstala apenas "
                    "o prompt de sistema.",
     "module": "tests.test_chat", "class": "ChatSessionTest",
     "method": "test_clear_keeps_system_prompt",
     "tags": ["chat", "clear", "contexto"], "offline": True},

    {"id": "T05",
     "name": "Payload da Groq inclui as tools",
     "description": "O JSON enviado à API carrega as definições das "
                    "ferramentas e tool_choice.",
     "module": "tests.test_groq_client", "class": "PayloadTest",
     "method": "test_payload_includes_tools",
     "tags": ["groq", "tools", "payload"], "offline": True},

    {"id": "T06",
     "name": "Parser reconhece tool_calls",
     "description": "Uma resposta com tool_calls e sem texto é interpretada "
                    "corretamente.",
     "module": "tests.test_groq_client", "class": "PayloadTest",
     "method": "test_parse_tool_calls",
     "tags": ["groq", "tools", "parser"], "offline": True},

    {"id": "T07",
     "name": "Tool Registry valida a lista branca",
     "description": "Uma ferramenta registrada é encontrada; um nome fora da "
                    "lista branca é rejeitado.",
     "module": "tests.test_tools", "class": "RegistryTest",
     "method": "test_whitelist",
     "tags": ["tools", "registry", "seguranca"], "offline": True},

    {"id": "T08",
     "name": "Busca fuzzy com correspondência exata",
     "description": "Uma pergunta escrita corretamente encontra o documento "
                    "certo da base de conhecimento.",
     "module": "tests.test_knowledge", "class": "FuzzySearchTest",
     "method": "test_exact_match",
     "tags": ["fuzzy", "busca", "knowledge"], "offline": True},

    {"id": "T09",
     "name": "Busca fuzzy com erro de digitação",
     "description": "Mesmo com 'doker' e 'jyton' escritos errados, o "
                    "documento de Docker é encontrado.",
     "module": "tests.test_knowledge", "class": "FuzzySearchTest",
     "method": "test_typo_match",
     "tags": ["fuzzy", "busca", "typo", "knowledge"], "offline": True},

    {"id": "T10",
     "name": "Knowledge Search respeita top_k",
     "description": "A busca nunca devolve mais trechos do que o limite "
                    "pedido.",
     "module": "tests.test_knowledge", "class": "FuzzySearchTest",
     "method": "test_top_k_limit",
     "tags": ["fuzzy", "busca", "knowledge", "limite"], "offline": True},

    {"id": "T11",
     "name": "SQLite cria todas as tabelas",
     "description": "A conexão JDBC cria as cinco tabelas do schema.",
     "module": "tests.test_database", "class": "DatabaseTest",
     "method": "test_schema_tables",
     "tags": ["banco", "sqlite", "jdbc", "database"], "offline": True},

    {"id": "T12",
     "name": "Interação é salva corretamente",
     "description": "Sessão, interação, mensagens e execução de ferramenta "
                    "são gravadas e recuperadas.",
     "module": "tests.test_database", "class": "DatabaseTest",
     "method": "test_interaction_roundtrip",
     "tags": ["banco", "sqlite", "jdbc", "historico"], "offline": True},

    {"id": "T13",
     "name": "Métricas de tokens, cache e latência",
     "description": "As agregações SQL calculam totais, médias e a taxa de "
                    "acerto do cache.",
     "module": "tests.test_metrics", "class": "MetricsTest",
     "method": "test_usage_metrics",
     "tags": ["metricas", "tokens", "cache", "latencia"], "offline": True},

    {"id": "T14",
     "name": "Busca fuzzy no histórico de conversas",
     "description": "Uma conversa antiga é recuperada mesmo com palavras "
                    "diferentes das originais.",
     "module": "tests.test_metrics", "class": "HistorySearchTest",
     "method": "test_history_fuzzy_search",
     "tags": ["fuzzy", "historico", "banco"], "offline": True},

    {"id": "T15",
     "name": "Janela de contexto deslizante",
     "description": "O contexto mantém apenas as últimas rodadas, sem nunca "
                    "separar um pedido de ferramenta do seu resultado.",
     "module": "tests.test_chat", "class": "ChatSessionTest",
     "method": "test_context_window",
     "tags": ["chat", "contexto", "janela", "tokens"], "offline": True},

    {"id": "T16",
     "name": "Adapter Caelum Stella e auditoria redigida",
     "description": "Valida documentos via Caelum Stella, limita lotes e não "
                    "persiste documentos brutos na cópia de auditoria.",
     "module": "tests.test_stella", "class": "StellaServiceTest",
     "method": "test_cpf_cnpj_transform_and_catalog",
     "tags": ["stella", "cpf", "cnpj", "privacidade", "tools"], "offline": True},

    {"id": "T17",
     "name": "Roteamento determinístico para tools Stella",
     "description": "Perguntas inequívocas de validação, formatação, geração, "
                    "extenso, capabilities e lote forçam a tool Stella certa.",
     "module": "tests.test_stella_routing", "class": "StellaRoutingTest",
     "method": "test_routes_document_intents",
     "tags": ["stella", "routing", "tools", "seguranca"], "offline": True},

    {"id": "T90",
     "name": "Integração real com a Groq",
     "description": "Faz uma chamada verdadeira à API da Groq. Consome tokens "
                    "e exige GROQ_API_KEY; não roda na execução padrão.",
     "module": "tests.test_groq_client", "class": "GroqIntegrationTest",
     "method": "test_real_request",
     "tags": ["integracao", "groq", "online"], "offline": False},
]


def all_tests():
    return list(TESTS)


def offline_tests():
    return [test for test in TESTS if test["offline"]]


def find(identifier):
    """Localiza um teste pelo identificador (T01, t01...)."""
    if not identifier:
        return None
    wanted = identifier.strip().upper()
    for test in TESTS:
        if test["id"].upper() == wanted:
            return test
    return None


def select(target="all"):
    """
    Converte o alvo pedido em uma lista de testes.

    Aceita "all", identificadores separados por vírgula ("T08,T09") ou uma
    palavra-chave que casa com nome, descrição ou tags ("fuzzy", "banco").
    """
    if target is None:
        target = "all"
    target = target.strip()

    if target == "" or target.lower() in ("all", "todos", "tudo", "*"):
        return offline_tests()

    selected = []
    seen = set()
    for token in target.replace(";", ",").split(","):
        token = token.strip()
        if not token:
            continue

        direct = find(token)
        if direct is not None:
            if direct["id"] not in seen:
                seen.add(direct["id"])
                selected.append(direct)
            continue

        needle = token.lower()
        for test in TESTS:
            haystack = " ".join([test["id"], test["name"], test["description"]]
                                + test["tags"]).lower()
            if needle in haystack and test["id"] not in seen:
                seen.add(test["id"])
                selected.append(test)

    selected.sort(key=lambda test: test["id"])
    return selected


# ---------------------------------------------------------------------------
# Execução
# ---------------------------------------------------------------------------
def _load_case(entry):
    module = __import__(entry["module"], {}, {}, ["*"])
    case_class = getattr(module, entry["class"])
    return case_class(entry["method"])


def _key(entry):
    return "%s.%s.%s" % (entry["module"], entry["class"], entry["method"])


def _case_key(case):
    return "%s.%s.%s" % (case.__class__.__module__,
                         case.__class__.__name__,
                         case._testMethodName)


def run(target="all"):
    """Executa os testes selecionados e devolve um resultado estruturado."""
    selected = select(target)

    if not selected:
        return {
            "alvo": target,
            "erro": "Nenhum teste corresponde a '%s'." % target,
            "total": 0,
            "executados": 0,
            "passaram": 0,
            "falharam": 0,
            "erros": 0,
            "tempo_ms": 0,
            "testes": [],
        }

    suite = unittest.TestSuite()
    lookup = {}
    load_errors = []
    for entry in selected:
        try:
            suite.addTest(_load_case(entry))
            lookup[_key(entry)] = entry
        except (ImportError, AttributeError) as error:
            load_errors.append({"id": entry["id"], "nome": entry["name"],
                                "detalhe": unicode(error)})

    stream = StringIO()
    runner = unittest.TextTestRunner(stream=stream, verbosity=2)

    started = System.currentTimeMillis()
    result = runner.run(suite)
    elapsed_ms = System.currentTimeMillis() - started

    problems = {}
    for case, traceback in list(result.failures):
        problems[_case_key(case)] = ("falhou", _last_line(traceback))
    for case, traceback in list(result.errors):
        problems[_case_key(case)] = ("erro", _last_line(traceback))

    detalhes = []
    for entry in selected:
        if entry["id"] in [item["id"] for item in load_errors]:
            continue
        status, detail = problems.get(_key(entry), ("passou", None))
        detalhes.append({
            "id": entry["id"],
            "nome": entry["name"],
            "situacao": status,
            "detalhe": detail,
        })

    return {
        "alvo": target,
        "total": len(selected),
        "executados": result.testsRun,
        "passaram": result.testsRun - len(result.failures) - len(result.errors),
        "falharam": len(result.failures),
        "erros": len(result.errors) + len(load_errors),
        "tempo_ms": int(elapsed_ms),
        "sucesso": result.wasSuccessful() and not load_errors,
        "testes": detalhes,
        "falhas_de_carga": load_errors,
    }


def _last_line(traceback_text):
    """Última linha útil de um traceback -- a mensagem do assert."""
    lines = [line.strip() for line in (traceback_text or "").splitlines()
             if line.strip()]
    return lines[-1] if lines else None
