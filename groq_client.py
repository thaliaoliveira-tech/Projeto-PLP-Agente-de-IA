# -*- coding: utf-8 -*-
"""
groq_client.py -- Cliente HTTP da API da Groq escrito em Python, mas usando
exclusivamente as APIs de rede e de entrada/saída da plataforma **Java**.

Este é o arquivo mais importante do projeto do ponto de vista acadêmico.
Nenhuma biblioteca HTTP de Python é utilizada (nada de requests, urllib2,
httplib, groq ou openai): toda a comunicação é feita por classes Java
invocadas diretamente a partir do código Python, o que só é possível porque o
programa é executado pelo Jython, sobre a JVM.

Além do chat comum, o cliente suporta **tool calling**: as definições das
ferramentas seguem no corpo da requisição e a resposta pode conter
``tool_calls`` em vez de texto.

APIs Java utilizadas neste módulo:

    java.net.URL                  -> representa o endpoint da Groq
    java.net.HttpURLConnection    -> conexão HTTP/HTTPS e códigos de status
    java.io.OutputStreamWriter    -> escreve o JSON da requisição no socket
    java.io.InputStreamReader     -> lê os bytes da resposta como texto UTF-8
    java.io.BufferedReader        -> lê a resposta linha a linha
    java.lang.StringBuilder       -> concatena a resposta de forma eficiente
    java.lang.System              -> currentTimeMillis(), para medir a latência
    java.net.UnknownHostException,
    java.net.ConnectException,
    java.net.SocketTimeoutException,
    java.io.IOException           -> exceções Java capturadas por "except" do
                                     Python

Fluxo de uma chamada:

    URL -> openConnection() -> HttpURLConnection -> POST
        -> Authorization: Bearer GROQ_API_KEY
        -> Content-Type: application/json
        -> OutputStreamWriter escreve o JSON (mensagens + tools)
        -> Groq processa com openai/gpt-oss-120b
        -> InputStreamReader + BufferedReader leem a resposta
        -> json.loads devolve conteúdo OU tool_calls ao Python
"""
from __future__ import unicode_literals

import json
import re

# ---------------------------------------------------------------------------
# Classes Java importadas como se fossem módulos Python.
# ---------------------------------------------------------------------------
from java.net import URL
from java.net import HttpURLConnection
from java.net import UnknownHostException
from java.net import ConnectException
from java.net import NoRouteToHostException
from java.net import SocketTimeoutException
from java.net import MalformedURLException
from java.io import OutputStreamWriter
from java.io import InputStreamReader
from java.io import BufferedReader
from java.io import IOException
from java.lang import StringBuilder
from java.lang import System
from java.lang import Thread as JavaThread

import config


CHARSET = "UTF-8"
USER_AGENT = "jython-ai-agent/2.0 (Jython; java.net.HttpURLConnection)"

# A Groq informa quanto esperar na própria mensagem de erro do HTTP 429.
_RETRY_HINT = re.compile(r"try again in ([0-9.]+)\s*s", re.IGNORECASE)


class GroqError(Exception):
    """
    Erro de comunicação com a Groq, já traduzido para uma mensagem amigável.

    message -> texto pronto para ser exibido ao usuário
    status  -> código HTTP, quando houver
    detail  -> mensagem técnica devolvida pela API, quando houver
    """

    def __init__(self, message, status=None, detail=None):
        Exception.__init__(self, message)
        self.message = message
        self.status = status
        self.detail = detail
        self.attempts = 1
        self.retry_wait_ms = 0


class ToolCall(object):
    """Uma solicitação de execução de ferramenta feita pelo modelo."""

    def __init__(self, call_id, name, arguments, raw_arguments=None):
        self.id = call_id
        self.name = name
        self.arguments = arguments if arguments is not None else {}
        self.raw_arguments = raw_arguments

    def to_message_part(self):
        """Formato exigido pela API ao reenviar a chamada no histórico."""
        return {
            "id": self.id,
            "type": "function",
            "function": {
                "name": self.name,
                "arguments": self.raw_arguments
                             if self.raw_arguments is not None
                             else json.dumps(self.arguments, ensure_ascii=False),
            },
        }

    def __repr__(self):
        return "<ToolCall %s %s>" % (self.name, self.id)


class GroqReply(object):
    """Resposta já processada da API (texto final ou pedido de ferramentas)."""

    def __init__(self, content, tool_calls, finish_reason, model, usage,
                 elapsed_ms, attempts=1, retry_wait_ms=0, reasoning=None):
        self.content = content
        # O gpt-oss é um modelo de raciocínio: além do texto final, devolve o
        # raciocínio em um campo separado. Ele PRECISA voltar ao histórico na
        # mensagem que pediu ferramentas -- veja ChatSession.add_assistant_tool_calls.
        self.reasoning = reasoning
        self.tool_calls = tool_calls or []
        self.finish_reason = finish_reason
        self.model = model
        self.usage = usage or {}
        self.elapsed_ms = elapsed_ms
        # Quantas requisições HTTP foram necessárias e quanto tempo o cliente
        # passou esperando por causa de HTTP 429/5xx.
        self.attempts = attempts
        self.retry_wait_ms = retry_wait_ms

    @property
    def has_tool_calls(self):
        return len(self.tool_calls) > 0

    @property
    def total_tokens(self):
        return self.usage.get("total_tokens")

    @property
    def prompt_tokens(self):
        return self.usage.get("prompt_tokens")

    @property
    def completion_tokens(self):
        return self.usage.get("completion_tokens")

    @property
    def cached_tokens(self):
        details = self.usage.get("prompt_tokens_details") or {}
        return details.get("cached_tokens", 0) or 0

    def __repr__(self):
        return "<GroqReply model=%s tools=%d tokens=%s elapsed=%sms>" % (
            self.model, len(self.tool_calls), self.total_tokens,
            self.elapsed_ms)


class GroqClient(object):
    """Cliente da Chat Completions API da Groq construído sobre java.net/java.io."""

    def __init__(self, api_key=None, model=None, api_url=None,
                 temperature=None, max_completion_tokens=None,
                 connect_timeout_ms=None, read_timeout_ms=None,
                 max_retries=None, on_retry=None, reasoning_effort=None):
        self.api_key = api_key or config.GROQ_API_KEY
        self.model = model or config.GROQ_MODEL
        self.api_url = api_url or config.GROQ_API_URL
        self.temperature = (config.TEMPERATURE
                            if temperature is None else temperature)
        self.max_completion_tokens = (config.MAX_COMPLETION_TOKENS
                                      if max_completion_tokens is None
                                      else max_completion_tokens)
        self.connect_timeout_ms = (config.CONNECT_TIMEOUT_MS
                                   if connect_timeout_ms is None
                                   else connect_timeout_ms)
        self.read_timeout_ms = (config.READ_TIMEOUT_MS
                                if read_timeout_ms is None else read_timeout_ms)
        self.max_retries = (config.GROQ_MAX_RETRIES
                            if max_retries is None else max_retries)
        self.reasoning_effort = (config.REASONING_EFFORT
                                 if reasoning_effort is None
                                 else reasoning_effort)
        self.on_retry = on_retry

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------
    def chat(self, messages, tools=None, tool_choice="auto"):
        """
        Envia a lista de mensagens (e, opcionalmente, as definições das
        ferramentas) para a Groq e devolve um ``GroqReply``.

        Erros temporários (HTTP 429 e 5xx) são repetidos automaticamente,
        respeitando o tempo de espera que a própria Groq informa. Lança
        ``GroqError`` quando não há mais o que tentar.
        """
        payload = self._build_payload(messages, tools, tool_choice)
        attempt = 0
        waited_ms = 0

        while True:
            # java.lang.System.currentTimeMillis() -- latência medida com Java.
            started = System.currentTimeMillis()
            status, body = self._post(payload)
            elapsed_ms = System.currentTimeMillis() - started

            if status == HttpURLConnection.HTTP_OK:
                return self._parse_reply(body, elapsed_ms,
                                         attempts=attempt + 1,
                                         retry_wait_ms=waited_ms)

            error = self._http_error(status, body)

            if attempt >= self.max_retries or not _is_retryable(status):
                error.attempts = attempt + 1
                error.retry_wait_ms = waited_ms
                raise error

            wait_ms = _retry_delay_ms(error.detail, attempt)
            attempt += 1
            waited_ms += wait_ms
            self._notify_retry(attempt, wait_ms, status)
            JavaThread.sleep(wait_ms)              # java.lang.Thread.sleep

    def _notify_retry(self, attempt, wait_ms, status):
        if self.on_retry is None:
            return
        try:
            self.on_retry(attempt, wait_ms, status)
        except Exception:
            pass

    def ask(self, question, system_prompt=None):
        """Atalho para uma pergunta única, sem histórico."""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": question})
        return self.chat(messages)

    # ------------------------------------------------------------------
    # Montagem do JSON enviado
    # ------------------------------------------------------------------
    def _build_payload(self, messages, tools=None, tool_choice="auto"):
        body = {
            "model": self.model,
            "messages": list(messages),
            "temperature": self.temperature,
            "max_completion_tokens": self.max_completion_tokens,
            "stream": False,
        }
        if self.reasoning_effort:
            # O gpt-oss sempre raciocina antes de responder; este parâmetro diz
            # quanto. Cada nível a mais custa tokens de saída e latência.
            body["reasoning_effort"] = self.reasoning_effort
        if tools:
            # As definições das ferramentas ficam estáveis entre requisições:
            # isso permite que o prompt caching da Groq as reaproveite.
            body["tools"] = list(tools)
            body["tool_choice"] = tool_choice
        # ensure_ascii=True: caracteres acentuados viajam como \uXXXX, o que
        # elimina qualquer ambiguidade de codificação no transporte.
        return json.dumps(body, ensure_ascii=True)

    # ------------------------------------------------------------------
    # Transporte HTTP -- 100% Java
    # ------------------------------------------------------------------
    def _open_connection(self):
        """Cria e configura a conexão HTTPS usando java.net."""
        url = URL(self.api_url)                     # java.net.URL
        connection = url.openConnection()           # java.net.HttpURLConnection

        connection.setRequestMethod("POST")
        connection.setRequestProperty("Content-Type",
                                      "application/json; charset=utf-8")
        connection.setRequestProperty("Authorization", "Bearer " + self.api_key)
        connection.setRequestProperty("Accept", "application/json")
        connection.setRequestProperty("User-Agent", USER_AGENT)
        connection.setConnectTimeout(self.connect_timeout_ms)
        connection.setReadTimeout(self.read_timeout_ms)
        connection.setUseCaches(False)
        connection.setDoOutput(True)                # habilita o corpo do POST
        return connection

    def _post(self, payload):
        """
        Executa o POST e devolve (status, corpo_da_resposta).

        Todas as exceções Java (java.io.IOException e suas filhas) são
        capturadas aqui e convertidas em GroqError com mensagem amigável.
        """
        connection = None
        try:
            connection = self._open_connection()

            # ---- envio do JSON: java.io.OutputStreamWriter ---------------
            writer = OutputStreamWriter(connection.getOutputStream(), CHARSET)
            try:
                writer.write(payload)
                writer.flush()
            finally:
                writer.close()

            # ---- leitura da resposta -------------------------------------
            status = connection.getResponseCode()
            if status < 400:
                stream = connection.getInputStream()
            else:
                stream = connection.getErrorStream()

            return status, self._read_stream(stream)

        except MalformedURLException:
            raise GroqError(
                "[ERRO] A URL da API da Groq é inválida:\n"
                "       %s\n"
                "       Verifique a variável de ambiente GROQ_API_URL."
                % self.api_url)
        except UnknownHostException as error:
            raise GroqError(
                "[ERRO] Não foi possível conectar à API da Groq.\n"
                "       O endereço %s não pôde ser resolvido.\n"
                "       Verifique sua conexão com a internet."
                % (error.getMessage() or "api.groq.com"))
        except (ConnectException, NoRouteToHostException):
            raise GroqError(
                "[ERRO] Não foi possível conectar à API da Groq.\n"
                "       Verifique sua conexão com a internet, proxy ou firewall.")
        except SocketTimeoutException:
            raise GroqError(
                "[ERRO] A Groq demorou demais para responder (timeout).\n"
                "       Tente novamente em instantes.")
        except IOException as error:
            raise GroqError(
                "[ERRO] Falha de comunicação com a API da Groq.\n"
                "       Detalhe (java.io.IOException): %s"
                % self._describe(error))
        finally:
            if connection is not None:
                connection.disconnect()

    def _read_stream(self, stream):
        """Lê um InputStream Java como texto UTF-8 usando BufferedReader."""
        if stream is None:
            return ""
        reader = BufferedReader(InputStreamReader(stream, CHARSET))
        buffer = StringBuilder()                    # java.lang.StringBuilder
        try:
            line = reader.readLine()
            while line is not None:
                buffer.append(line)
                buffer.append("\n")
                line = reader.readLine()
        finally:
            reader.close()
        return buffer.toString()

    # ------------------------------------------------------------------
    # Interpretação da resposta
    # ------------------------------------------------------------------
    def _parse_reply(self, body, elapsed_ms, attempts=1, retry_wait_ms=0):
        try:
            data = json.loads(body)
        except ValueError:
            raise GroqError(
                "[ERRO] A Groq devolveu uma resposta que não é um JSON válido.")

        choices = data.get("choices")
        if not choices:
            raise GroqError(
                "[ERRO] A Groq respondeu sem nenhuma escolha (choices vazio).")

        choice = choices[0]
        message = choice.get("message") or {}
        content = message.get("content")
        reasoning = message.get("reasoning")
        finish_reason = choice.get("finish_reason")
        tool_calls = self._parse_tool_calls(message.get("tool_calls"))

        if not tool_calls and (content is None or content.strip() == ""):
            # Modelos de raciocínio podem devolver conteúdo vazio quando o
            # limite de tokens é atingido antes da resposta final.
            if finish_reason == "length":
                raise GroqError(
                    "[ERRO] A resposta foi interrompida por limite de tokens.\n"
                    "       Aumente GROQ_MAX_TOKENS (atual: %s)."
                    % self.max_completion_tokens)
            raise GroqError("[ERRO] A Groq devolveu uma resposta vazia.")

        return GroqReply(
            content=content.strip() if content else None,
            tool_calls=tool_calls,
            finish_reason=finish_reason,
            model=data.get("model", self.model),
            usage=data.get("usage"),
            elapsed_ms=elapsed_ms,
            attempts=attempts,
            retry_wait_ms=retry_wait_ms,
            reasoning=reasoning,
        )

    def _parse_tool_calls(self, raw_tool_calls):
        """Converte o campo ``tool_calls`` da resposta em objetos ToolCall."""
        if not raw_tool_calls:
            return []

        calls = []
        for item in raw_tool_calls:
            function = item.get("function") or {}
            raw_arguments = function.get("arguments")
            try:
                arguments = json.loads(raw_arguments) if raw_arguments else {}
            except ValueError:
                arguments = {}
            if not isinstance(arguments, dict):
                arguments = {}
            calls.append(ToolCall(
                call_id=item.get("id"),
                name=function.get("name"),
                arguments=arguments,
                raw_arguments=raw_arguments,
            ))
        return calls

    # ------------------------------------------------------------------
    # Tradução de erros HTTP em mensagens amigáveis
    # ------------------------------------------------------------------
    def _http_error(self, status, body):
        detail = self._extract_error_detail(body)

        if status in (HttpURLConnection.HTTP_UNAUTHORIZED,
                      HttpURLConnection.HTTP_FORBIDDEN):
            message = ("[ERRO] Não foi possível autenticar na Groq (HTTP %d).\n"
                       "       Verifique sua GROQ_API_KEY." % status)
        elif status == 429:
            message = ("[ERRO] Limite de requisições da Groq atingido (HTTP 429).\n"
                       "       Tente novamente posteriormente.")
        elif status == HttpURLConnection.HTTP_NOT_FOUND:
            message = ("[ERRO] Endpoint ou modelo não encontrado (HTTP 404).\n"
                       "       Modelo configurado: %s" % self.model)
        elif status == HttpURLConnection.HTTP_BAD_REQUEST:
            message = ("[ERRO] A Groq recusou a requisição (HTTP 400).\n"
                       "       Modelo configurado: %s" % self.model)
        elif status >= 500:
            message = ("[ERRO] A Groq retornou erro HTTP %d (indisponibilidade\n"
                       "       temporária do serviço). Tente novamente em instantes."
                       % status)
        else:
            message = "[ERRO] A Groq retornou HTTP %d." % status

        if detail:
            message = message + "\n       Detalhe da API: " + detail

        return GroqError(message, status=status, detail=detail)

    def _extract_error_detail(self, body):
        """Extrai error.message do corpo de erro devolvido pela Groq."""
        if not body:
            return None
        try:
            data = json.loads(body)
        except ValueError:
            text = body.strip()
            return text[:300] if text else None
        error = data.get("error")
        if isinstance(error, dict):
            return error.get("message")
        if isinstance(error, basestring):
            return error
        return None

    def _describe(self, java_exception):
        """Descrição curta de uma exceção Java (classe + mensagem)."""
        try:
            name = java_exception.getClass().getName()
            text = java_exception.getMessage()
        except AttributeError:
            return str(java_exception)
        if text:
            return "%s: %s" % (name, text)
        return name


# ---------------------------------------------------------------------------
# Política de repetição para erros temporários
# ---------------------------------------------------------------------------
def _is_retryable(status):
    """429 (limite de requisições) e 5xx são temporários; o resto, não."""
    return status == 429 or status >= 500


def _retry_delay_ms(detail, attempt):
    """
    Quanto esperar antes de tentar de novo.

    A Groq costuma dizer na mensagem de erro quanto falta ("try again in
    5.15s"); quando não diz, usamos backoff exponencial.
    """
    if detail:
        match = _RETRY_HINT.search(detail)
        if match:
            try:
                wait = float(match.group(1)) * 1000.0 + 400.0
                return int(min(wait, config.GROQ_RETRY_MAX_WAIT_MS))
            except ValueError:
                pass
    wait = 2000 * (2 ** attempt)
    return int(min(wait, config.GROQ_RETRY_MAX_WAIT_MS))
