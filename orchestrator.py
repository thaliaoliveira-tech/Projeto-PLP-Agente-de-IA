# -*- coding: utf-8 -*-
"""
orchestrator.py -- o laço agentivo (agentic loop) do Jython AI Agent.

É aqui que o projeto deixa de ser um chat simples e vira um agente. Em vez de
mandar a pergunta e imprimir a resposta, o orquestrador conduz um ciclo:

     1. grava a pergunta do usuário
     2. envia histórico + definições das ferramentas para a Groq
     3. se a resposta tiver conteúdo -> resposta final
     4. se a resposta tiver tool_calls:
            valida e executa a ferramenta localmente
            grava a execução no banco
            devolve o resultado ao modelo como mensagem de papel "tool"
            volta ao passo 2
     5. tudo isso limitado por AGENT_MAX_ITERATIONS

Todas as chamadas à LLM e todas as execuções de ferramenta são gravadas no
SQLite, o que torna a execução inteiramente auditável.

APIs Java utilizadas neste módulo:

    java.lang.System.currentTimeMillis() -> duração de cada interação
"""
from __future__ import unicode_literals

import json

from java.lang import System

import config
from groq_client import GroqError
from stella.routing import forced_tool_for, tool_choice_for


# Limite de tamanho do resultado de uma ferramenta devolvido ao modelo.
MAX_TOOL_RESULT_CHARS = 3500

# Tipos de evento enviados ao terminal enquanto o agente trabalha.
EVENT_LLM = "llm"
EVENT_TOOL_START = "tool_start"
EVENT_TOOL_END = "tool_end"


class AgentResult(object):
    """Resultado de uma interação completa do agente."""

    def __init__(self, content=None, error=None, tool_results=None,
                 llm_calls=0, elapsed_ms=0, interaction_id=None,
                 usage=None, model=None):
        self.content = content
        self.error = error
        self.tool_results = tool_results or []
        self.llm_calls = llm_calls
        self.elapsed_ms = elapsed_ms
        self.interaction_id = interaction_id
        self.usage = usage or {}
        self.model = model

    @property
    def ok(self):
        return self.error is None

    @property
    def tools_used(self):
        return [result.name for result in self.tool_results]

    def __repr__(self):
        return "<AgentResult ok=%s llm_calls=%d tools=%s>" % (
            self.ok, self.llm_calls, self.tools_used)


class AgentOrchestrator(object):
    """Coordena o modelo, as ferramentas locais e a persistência."""

    def __init__(self, client, session, registry, interactions=None,
                 session_id=None, max_iterations=None, on_event=None,
                 context_turns=None):
        self.client = client
        self.session = session
        self.registry = registry
        self.interactions = interactions
        self.session_id = session_id
        self.max_iterations = max_iterations or config.AGENT_MAX_ITERATIONS
        self.context_turns = (config.AGENT_CONTEXT_TURNS
                              if context_turns is None else context_turns)
        self.on_event = on_event

    # ------------------------------------------------------------------
    # Interação completa
    # ------------------------------------------------------------------
    def ask(self, question):
        started = System.currentTimeMillis()
        interaction_id = self._start_interaction()

        # Janela deslizante: descarta as rodadas mais antigas antes de montar a
        # próxima requisição, para o contexto não crescer sem limite.
        self.session.trim_to_turns(self.context_turns - 1)

        # Ponto de retorno caso a interação falhe no meio do caminho.
        checkpoint = self.session.size()

        self.session.add_user(question)
        self._save_message(interaction_id, "user", question)

        schemas = self.registry.schemas()
        forced_tool = forced_tool_for(question)
        tool_results = []
        llm_calls = 0
        last_reply = None

        try:
            for iteration in range(self.max_iterations):
                # Para intenções Stella inequívocas, a primeira rodada deve
                # obrigatoriamente executar a tool correspondente. Sem isso,
                # modelos podem calcular CPF/CNPJ ou responder por extenso no
                # próprio texto, ignorando a operação determinística local.
                choice = tool_choice_for(forced_tool) if iteration == 0 else "auto"
                reply = self.client.chat(self.session.messages(), tools=schemas,
                                         tool_choice=choice)
                llm_calls += 1
                last_reply = reply
                self._save_llm_call(interaction_id, iteration, reply)
                self._emit(EVENT_LLM, {"iteration": iteration + 1,
                                       "tool_calls": len(reply.tool_calls)})

                if not reply.has_tool_calls:
                    content = reply.content or ""
                    self.session.add_assistant(content)
                    self._save_message(interaction_id, "assistant", content)
                    elapsed = System.currentTimeMillis() - started
                    self._finish_interaction(interaction_id, elapsed, "ok")
                    return AgentResult(
                        content=content, tool_results=tool_results,
                        llm_calls=llm_calls, elapsed_ms=elapsed,
                        interaction_id=interaction_id,
                        usage=reply.usage, model=reply.model)

                # O modelo pediu ferramentas: registra o pedido no histórico.
                self.session.add_assistant_tool_calls(reply.content,
                                                      reply.tool_calls,
                                                      reply.reasoning)
                self._save_message(
                    interaction_id, "assistant",
                    "[tool_calls] " + ", ".join(
                        [call.name or "?" for call in reply.tool_calls]))

                for call in reply.tool_calls:
                    tool_results.append(
                        self._run_tool(interaction_id, call))

            # Saiu do laço sem resposta final.
            elapsed = System.currentTimeMillis() - started
            self.session.rollback_to(checkpoint)
            self._finish_interaction(interaction_id, elapsed, "limit")
            return AgentResult(
                error=("[ERRO] Limite de execução de ferramentas atingido "
                       "(%d iterações).\n"
                       "       Reformule a pergunta ou aumente "
                       "AGENT_MAX_ITERATIONS." % self.max_iterations),
                tool_results=tool_results, llm_calls=llm_calls,
                elapsed_ms=elapsed, interaction_id=interaction_id)

        except GroqError as error:
            elapsed = System.currentTimeMillis() - started
            self.session.rollback_to(checkpoint)
            self._finish_interaction(interaction_id, elapsed, "error",
                                     error.message)
            return AgentResult(error=error.message, tool_results=tool_results,
                               llm_calls=llm_calls, elapsed_ms=elapsed,
                               interaction_id=interaction_id)

    # ------------------------------------------------------------------
    # Execução de uma ferramenta
    # ------------------------------------------------------------------
    def _run_tool(self, interaction_id, call):
        self._emit(EVENT_TOOL_START, {"name": call.name,
                                      "arguments": call.arguments})

        result = self.registry.execute(call.name, call.arguments)

        self._save_tool_execution(interaction_id, call, result)

        payload = self._serialize(result.result)
        self.session.add_tool_result(call.id, call.name, payload)
        self._save_message(interaction_id, "tool", payload)

        self._emit(EVENT_TOOL_END, {"name": call.name,
                                    "elapsed_ms": result.elapsed_ms,
                                    "success": result.success})
        return result

    def _serialize(self, value):
        try:
            text = json.dumps(value, ensure_ascii=False)
        except (TypeError, ValueError):
            text = unicode(value)
        if len(text) > MAX_TOOL_RESULT_CHARS:
            text = (text[:MAX_TOOL_RESULT_CHARS]
                    + '... (resultado truncado pelo orquestrador)')
        return text

    # ------------------------------------------------------------------
    # Eventos para o terminal
    # ------------------------------------------------------------------
    def _emit(self, kind, payload):
        if self.on_event is not None:
            try:
                self.on_event(kind, payload)
            except Exception:
                pass

    # ------------------------------------------------------------------
    # Persistência (silenciosa: o agente nunca quebra por causa do banco)
    # ------------------------------------------------------------------
    def _start_interaction(self):
        if self.interactions is None or self.session_id is None:
            return None
        try:
            return self.interactions.start_interaction(self.session_id)
        except Exception:
            return None

    def _finish_interaction(self, interaction_id, elapsed_ms, status,
                            error=None):
        if self.interactions is None or interaction_id is None:
            return
        try:
            self.interactions.finish_interaction(interaction_id, elapsed_ms,
                                                 status, error)
        except Exception:
            pass

    def _save_message(self, interaction_id, role, content):
        if self.interactions is None or self.session_id is None:
            return
        try:
            self.interactions.save_message(self.session_id, interaction_id,
                                           role, content)
        except Exception:
            pass

    def _save_llm_call(self, interaction_id, index, reply):
        if self.interactions is None or interaction_id is None:
            return
        try:
            self.interactions.save_llm_call(interaction_id, index, reply)
        except Exception:
            pass

    def _save_tool_execution(self, interaction_id, call, result):
        if self.interactions is None or interaction_id is None:
            return
        try:
            self.interactions.save_tool_execution(
                interaction_id, call.id, call.name, result.audit_arguments,
                result.audit_result, result.elapsed_ms, result.success,
                result.error)
        except Exception:
            pass
