# -*- coding: utf-8 -*-
"""Registro, validação e auditoria segura das ferramentas do agente."""
from __future__ import unicode_literals

from java.lang import System


WHITELIST = (
    "search_project_knowledge", "list_project_tests", "run_project_tests",
    "search_chat_history", "get_recent_interactions", "get_usage_metrics",
    "stella_validate_document", "stella_transform_document",
    "stella_generate_document", "stella_number_to_words",
    "stella_capabilities", "stella_validate_batch",
)


class ToolError(Exception):
    """Erro controlado de validação ou execução de ferramenta."""
    def __init__(self, message):
        Exception.__init__(self, message)
        self.message = message


class ToolContext(object):
    """Dependências compartilhadas pelas ferramentas locais."""
    def __init__(self, knowledge=None, interactions=None, metrics=None,
                 session_id=None, test_runner=None, stella=None):
        self.knowledge = knowledge
        self.interactions = interactions
        self.metrics = metrics
        self.session_id = session_id
        self.test_runner = test_runner
        self.stella = stella


class Tool(object):
    """Uma operação local explicitamente permitida ao modelo."""
    def __init__(self, name, description, parameters, handler, required=None,
                 sensitive_fields=None, category=None, audit_policy="store"):
        self.name = name
        self.description = description
        self.parameters = parameters or {}
        self.handler = handler
        self.required = list(required or [])
        self.sensitive_fields = list(sensitive_fields or [])
        self.category = category
        self.audit_policy = audit_policy

    def schema(self):
        return {"type": "function", "function": {
            "name": self.name, "description": self.description,
            "parameters": {"type": "object", "properties": self.parameters,
                           "required": self.required}}}

    def __repr__(self):
        return "<Tool %s>" % self.name


class ToolResult(object):
    """Resultado para a LLM, com uma versão independente para auditoria."""
    def __init__(self, name, result, elapsed_ms, success=True, error=None,
                 arguments=None, audit_arguments=None, audit_result=None):
        self.name = name
        self.result = result
        self.elapsed_ms = elapsed_ms
        self.success = success
        self.error = error
        self.arguments = arguments or {}
        self.audit_arguments = (audit_arguments if audit_arguments is not None
                                else self.arguments)
        self.audit_result = audit_result if audit_result is not None else result

    def __repr__(self):
        return "<ToolResult %s success=%s %sms>" % (
            self.name, self.success, self.elapsed_ms)


class ToolRegistry(object):
    """Whitelist, schema subset e despacho determinístico das ferramentas."""
    def __init__(self, whitelist=WHITELIST):
        self.whitelist = tuple(whitelist)
        self._tools = {}
        self._order = []

    def register(self, tool):
        if tool.name not in self.whitelist:
            raise ToolError("Ferramenta '%s' fora da lista branca do projeto."
                            % tool.name)
        if tool.name not in self._tools:
            self._order.append(tool.name)
        self._tools[tool.name] = tool
        return tool

    def register_all(self, tools):
        for tool in tools:
            self.register(tool)
        return self

    def names(self):
        return list(self._order)

    def get(self, name):
        return self._tools.get(name)

    def has(self, name):
        return name in self._tools

    def schemas(self):
        return [self._tools[name].schema() for name in self._order]

    def __len__(self):
        return len(self._tools)

    def execute(self, name, arguments=None):
        """Executa uma tool e sempre devolve um ToolResult."""
        started = System.currentTimeMillis()
        arguments = arguments if isinstance(arguments, dict) else {}
        tool = self._tools.get(name)
        if tool is None:
            message = "Ferramenta inexistente: %s" % name
            return ToolResult(name, {"error": message,
                                     "ferramentas_disponiveis": self.names()},
                              System.currentTimeMillis() - started,
                              False, message, arguments)
        try:
            validated = validate_arguments(tool, arguments)
            result = tool.handler(**validated)
            if not isinstance(result, dict):
                result = {"resultado": result}
            return ToolResult(
                name, result, System.currentTimeMillis() - started, True,
                arguments=validated,
                audit_arguments=_audit_value(validated, tool.sensitive_fields,
                                             tool.audit_policy),
                audit_result=_audit_value(result, tool.sensitive_fields,
                                          tool.audit_policy))
        except ToolError as error:
            return ToolResult(name, {"error": error.message},
                              System.currentTimeMillis() - started, False,
                              error.message,
                              _audit_value(arguments, tool.sensitive_fields,
                                           tool.audit_policy))
        except Exception:
            message = "Falha ao executar %s." % name
            return ToolResult(name, {"error": message},
                              System.currentTimeMillis() - started, False,
                              message,
                              _audit_value(arguments, tool.sensitive_fields,
                                           tool.audit_policy))


def validate_arguments(tool, arguments):
    if not isinstance(arguments, dict):
        raise ToolError("Os argumentos devem ser um objeto JSON.")
    for required in tool.required:
        value = arguments.get(required)
        if value is None or (isinstance(value, basestring) and not value.strip()):
            raise ToolError("Parâmetro obrigatório ausente em %s: '%s'."
                            % (tool.name, required))
    validated = {}
    for key, schema in tool.parameters.items():
        if key in arguments and arguments[key] is not None:
            validated[str(key)] = _coerce(tool.name, key, schema, arguments[key])
    return validated


def _coerce(tool_name, key, schema, value):
    schema = schema or {}
    expected = schema.get("type", "string")
    if expected == "integer":
        try:
            converted = int(value)
        except (TypeError, ValueError):
            raise ToolError("Parâmetro '%s' de %s deve ser inteiro." %
                            (key, tool_name))
        _numeric_limits(tool_name, key, schema, converted)
        return converted
    if expected == "number":
        try:
            converted = float(value)
        except (TypeError, ValueError):
            raise ToolError("Parâmetro '%s' de %s deve ser numérico." %
                            (key, tool_name))
        _numeric_limits(tool_name, key, schema, converted)
        return converted
    if expected == "boolean":
        if isinstance(value, bool):
            return value
        if isinstance(value, basestring):
            return value.strip().lower() in ("true", "1", "sim", "yes")
        return bool(value)
    if expected == "array":
        if not isinstance(value, (list, tuple)):
            raise ToolError("Parâmetro '%s' de %s deve ser uma lista." %
                            (key, tool_name))
        _collection_limits(tool_name, key, schema, value)
        item_schema = schema.get("items") or {}
        return [_coerce(tool_name, "%s[]" % key, item_schema, item)
                for item in value]
    if expected == "object":
        if not isinstance(value, dict):
            raise ToolError("Parâmetro '%s' de %s deve ser um objeto JSON." %
                            (key, tool_name))
        properties = schema.get("properties") or {}
        for required in schema.get("required") or []:
            if required not in value or value[required] is None:
                raise ToolError("Campo obrigatório ausente em '%s': '%s'." %
                                (key, required))
        return dict((str(item_key),
                     _coerce(tool_name, "%s.%s" % (key, item_key),
                             properties[item_key], item_value)
                     if item_key in properties else item_value)
                    for item_key, item_value in value.items()
                    if item_value is not None)
    text = value if isinstance(value, basestring) else unicode(value)
    if schema.get("minLength") is not None and len(text) < schema["minLength"]:
        raise ToolError("Parâmetro '%s' de %s tem tamanho menor que o permitido."
                        % (key, tool_name))
    if schema.get("maxLength") is not None and len(text) > schema["maxLength"]:
        raise ToolError("Parâmetro '%s' de %s excede o tamanho permitido."
                        % (key, tool_name))
    options = schema.get("enum")
    if options and text not in options:
        raise ToolError("Parâmetro '%s' de %s deve ser um destes valores: %s."
                        % (key, tool_name, ", ".join(options)))
    return text


def _numeric_limits(tool_name, key, schema, value):
    if schema.get("minimum") is not None and value < schema["minimum"]:
        raise ToolError("Parâmetro '%s' de %s deve ser maior ou igual a %s." %
                        (key, tool_name, schema["minimum"]))
    if schema.get("maximum") is not None and value > schema["maximum"]:
        raise ToolError("Parâmetro '%s' de %s deve ser menor ou igual a %s." %
                        (key, tool_name, schema["maximum"]))


def _collection_limits(tool_name, key, schema, value):
    if schema.get("minItems") is not None and len(value) < schema["minItems"]:
        raise ToolError("Parâmetro '%s' de %s tem poucos itens." %
                        (key, tool_name))
    if schema.get("maxItems") is not None and len(value) > schema["maxItems"]:
        raise ToolError("Parâmetro '%s' de %s excede o limite de itens." %
                        (key, tool_name))


def _audit_value(value, sensitive_fields, audit_policy):
    if audit_policy == "omit":
        return {"audit": "omitted"}
    if audit_policy != "redact" or not sensitive_fields:
        return value
    return redact(value, sensitive_fields)


def redact(value, sensitive_fields):
    """Redige chaves sensíveis, inclusive em objetos e listas aninhados."""
    fields = set(sensitive_fields)
    if isinstance(value, dict):
        return dict((key, "***REDACTED***" if key in fields
                     else redact(item, fields)) for key, item in value.items())
    if isinstance(value, (list, tuple)):
        return [redact(item, fields) for item in value]
    return value
