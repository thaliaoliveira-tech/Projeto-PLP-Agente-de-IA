# -*- coding: utf-8 -*-
"""
chat.py -- Sessão de conversa do Jython AI Agent.

O histórico da conversa **não** é uma lista Python: é um
``java.util.ArrayList`` cujos elementos são ``java.util.LinkedHashMap``.
Cada mapa guarda "role" e "content" e, quando for o caso, os campos extras
exigidos pelo tool calling ("tool_calls" e "tool_call_id").

É isso que dá memória ao agente: a cada pergunta, todo o histórico é reenviado
ao modelo, e por isso ele lembra do que foi dito antes e do que as ferramentas
responderam.

APIs Java utilizadas neste módulo:

    java.util.ArrayList      -> armazena o histórico da conversa
    java.util.LinkedHashMap  -> representa cada mensagem, preservando a ordem
                                de inserção das chaves
    java.util.Collections    -> exposição somente-leitura do histórico
"""
from __future__ import unicode_literals

import json

# ---------------------------------------------------------------------------
# Estruturas de dados Java usadas diretamente pelo Python.
# ---------------------------------------------------------------------------
from java.util import ArrayList
from java.util import LinkedHashMap
from java.util import Collections

import config


ROLE_SYSTEM = "system"
ROLE_USER = "user"
ROLE_ASSISTANT = "assistant"
ROLE_TOOL = "tool"


def new_message(role, content, tool_calls_json=None, tool_call_id=None,
                name=None, reasoning=None):
    """Cria uma mensagem como um java.util.LinkedHashMap."""
    message = LinkedHashMap()
    message.put("role", role)
    message.put("content", content)
    if reasoning:
        message.put("reasoning", reasoning)
    if tool_calls_json is not None:
        message.put("tool_calls_json", tool_calls_json)
    if tool_call_id is not None:
        message.put("tool_call_id", tool_call_id)
    if name is not None:
        message.put("name", name)
    return message


class ChatSession(object):
    """Controla o histórico e o contexto da conversa."""

    def __init__(self, system_prompt=None):
        self.system_prompt = system_prompt or config.SYSTEM_PROMPT

        # java.util.ArrayList -- a estrutura de dados do histórico.
        self.history = ArrayList()
        self._install_system_prompt()

    # ------------------------------------------------------------------
    # Manipulação do histórico
    # ------------------------------------------------------------------
    def _install_system_prompt(self):
        self.history.add(new_message(ROLE_SYSTEM, self.system_prompt))

    def add_user(self, content):
        """Registra uma mensagem do usuário no ArrayList."""
        self.history.add(new_message(ROLE_USER, content))

    def add_assistant(self, content):
        """Registra uma resposta textual do modelo no ArrayList."""
        self.history.add(new_message(ROLE_ASSISTANT, content))

    def add_assistant_tool_calls(self, content, tool_calls, reasoning=None):
        """
        Registra a resposta em que o modelo pediu ferramentas.

        A lista de ``ToolCall`` é serializada como JSON dentro do mapa Java;
        ``messages()`` a devolve ao formato exigido pela API.

        O ``reasoning`` devolvido pelo gpt-oss precisa voltar junto nesta
        mensagem. Sem ele, o modelo perde a própria linha de raciocínio e passa
        a degenerar em repetição depois de algumas rodadas parecidas -- um
        comportamento reproduzido em teste durante o desenvolvimento.
        """
        parts = [call.to_message_part() for call in tool_calls]
        self.history.add(new_message(
            ROLE_ASSISTANT, content,
            tool_calls_json=json.dumps(parts, ensure_ascii=False),
            reasoning=reasoning))

    def add_tool_result(self, tool_call_id, tool_name, content):
        """Registra o resultado de uma ferramenta (papel ``tool``)."""
        self.history.add(new_message(
            ROLE_TOOL, content, tool_call_id=tool_call_id, name=tool_name))

    def drop_last(self):
        """
        Remove a última mensagem do histórico.

        Usado quando a chamada à Groq falha: assim a pergunta que não obteve
        resposta não é reenviada na próxima interação.
        """
        if self.history.size() > 1:
            self.history.remove(self.history.size() - 1)

    def rollback_to(self, size):
        """Desfaz o histórico até um tamanho anterior (usado em falhas)."""
        while self.history.size() > size and self.history.size() > 1:
            self.history.remove(self.history.size() - 1)

    def clear(self):
        """Executa /clear: esvazia o ArrayList e reinstala o prompt de sistema."""
        self.history.clear()
        self._install_system_prompt()

    def turn_starts(self):
        """Índices das mensagens de papel ``user`` -- o início de cada rodada."""
        starts = []
        for index in range(1, self.history.size()):
            if self.history.get(index).get("role") == ROLE_USER:
                starts.append(index)
        return starts

    def turns(self):
        """Quantas perguntas do usuário estão no contexto atual."""
        return len(self.turn_starts())

    def trim_to_turns(self, max_turns):
        """
        Janela de contexto deslizante: mantém o prompt de sistema e apenas as
        últimas ``max_turns`` perguntas (com suas respostas e resultados de
        ferramenta).

        Sem isso, cada pergunta reenvia a conversa inteira e fica mais cara que
        a anterior, até estourar o limite de tokens por minuto da API.

        O corte é sempre feito **antes de uma mensagem de papel "user"**, para
        nunca separar um pedido de ferramenta do resultado correspondente --
        a API rejeita um ``tool_call`` sem a resposta ``tool``, e vice-versa.

        Devolve quantas mensagens foram descartadas.
        """
        if max_turns is None:
            return 0

        starts = self.turn_starts()

        if max_turns <= 0:
            cut = self.history.size()
        else:
            if len(starts) <= max_turns:
                return 0
            cut = starts[len(starts) - max_turns]

        removed = 0
        while self.history.size() > 1 and removed < cut - 1:
            self.history.remove(1)
            removed += 1
        return removed

    # ------------------------------------------------------------------
    # Consulta
    # ------------------------------------------------------------------
    def messages(self):
        """
        Converte o histórico Java em uma lista de dicionários Python, no
        formato aceito pela API da Groq.

        O laço abaixo é um bom resumo do projeto: um ``for`` de Python
        iterando sobre um ``java.util.ArrayList``, e ``get()`` sendo chamado
        em um ``java.util.LinkedHashMap``.
        """
        payload = []
        for message in self.history:
            entry = {
                "role": message.get("role"),
                "content": message.get("content"),
            }
            reasoning = message.get("reasoning")
            if reasoning:
                entry["reasoning"] = reasoning
            tool_calls_json = message.get("tool_calls_json")
            if tool_calls_json:
                entry["tool_calls"] = json.loads(tool_calls_json)
            tool_call_id = message.get("tool_call_id")
            if tool_call_id:
                entry["tool_call_id"] = tool_call_id
            name = message.get("name")
            if name:
                entry["name"] = name
            payload.append(entry)
        return payload

    def java_history(self):
        """Devolve o histórico Java em modo somente-leitura."""
        return Collections.unmodifiableList(self.history)

    def size(self):
        return self.history.size()

    def exchanged_messages(self):
        """Quantidade de mensagens trocadas, sem contar o prompt de sistema."""
        return self.history.size() - 1

    def is_empty(self):
        """True quando ainda não houve nenhuma troca de mensagens."""
        return self.exchanged_messages() <= 0

    def backing_class(self):
        """Nome da classe Java que sustenta o histórico (java.util.ArrayList)."""
        return self.history.getClass().getName()

    def __len__(self):
        return self.history.size()

    def __repr__(self):
        return "<ChatSession %s mensagens=%d>" % (
            self.backing_class(), self.history.size())
