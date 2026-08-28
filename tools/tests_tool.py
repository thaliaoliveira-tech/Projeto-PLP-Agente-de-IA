# -*- coding: utf-8 -*-
"""
tools/tests_tool.py -- ferramentas ``list_project_tests`` e
``run_project_tests``.

O agente é capaz de listar e executar a própria suíte de testes. O usuário
nunca vê a saída crua do runner: a ferramenta devolve um resultado estruturado
e é o modelo que o transforma em uma resposta legível.
"""
from __future__ import unicode_literals

from tests import registry as test_registry
from tools.registry import Tool


def create_tools(context):
    runner = context.test_runner or test_registry

    def list_project_tests(only=None, detail=False):
        escolha = (only or "offline").lower()
        if escolha == "all":
            catalogo = runner.all_tests()
        elif escolha == "integration":
            catalogo = [t for t in runner.all_tests() if not t["offline"]]
        else:
            catalogo = runner.offline_tests()

        testes = []
        for teste in catalogo:
            item = {"id": teste["id"], "nome": teste["name"]}
            if not teste["offline"]:
                item["tipo"] = "integração (usa a Groq)"
            if detail:
                # Só sob pedido: as descrições completas custam ~500 tokens.
                item["descricao"] = teste["description"]
                item["tags"] = teste["tags"]
            testes.append(item)

        return {
            "filtro": escolha,
            "total": len(testes),
            "testes": testes,
            "observacao": ("T90 é um teste de integração: consome tokens da "
                           "Groq e só roda quando pedido explicitamente."),
        }

    def run_project_tests(target=None):
        alvo = target or "all"
        resultado = runner.run(alvo)

        if resultado.get("erro"):
            return resultado

        falhas = [teste for teste in resultado["testes"]
                  if teste["situacao"] != "passou"]
        resultado["resumo"] = (
            "%d de %d testes passaram em %d ms."
            % (resultado["passaram"], resultado["executados"],
               resultado["tempo_ms"]))
        resultado["falhas"] = falhas
        return resultado

    return [
        Tool(
            name="list_project_tests",
            description=(
                "Lista os testes automatizados do projeto, com identificador, "
                "nome e descrição. Use quando o usuário perguntar quais testes "
                "existem ou o que pode ser testado."),
            parameters={
                "only": {
                    "type": "string",
                    "enum": ["offline", "integration", "all"],
                    "description": "offline = os testes que não usam a Groq; "
                                   "integration = apenas o T90; all = todos. "
                                   "Padrão: offline.",
                },
                "detail": {
                    "type": "boolean",
                    "description": "true inclui a descrição completa e as tags "
                                   "de cada teste. Padrão: false (só id e "
                                   "nome), para economizar tokens.",
                },
            },
            required=[],
            handler=list_project_tests,
        ),
        Tool(
            name="run_project_tests",
            description=(
                "Executa a suíte de testes do projeto e devolve o resultado "
                "estruturado. O alvo pode ser 'all' (todos os testes "
                "offline), identificadores separados por vírgula (ex.: "
                "'T08,T09') ou uma palavra-chave que casa com o nome dos "
                "testes (ex.: 'fuzzy', 'banco', 'tools'). Use 'T90' apenas se "
                "o usuário pedir explicitamente um teste real contra a Groq."),
            parameters={
                "target": {
                    "type": "string",
                    "description": "all, identificadores (T08,T09) ou "
                                   "palavra-chave. Padrão: all.",
                },
            },
            required=[],
            handler=run_project_tests,
        ),
    ]
