"""Native tool contracts and local-only JSON Schema validation."""

from __future__ import annotations

import inspect
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, get_type_hints

from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError
from pydantic import ConfigDict, create_model

from .contracts import CoreError, Effect, Json, canonical, digest


def check_schema(schema: dict[str, Json]) -> None:
    if len(canonical(schema).encode()) > 65536:
        raise ValueError("schema too large")

    def walk(value: Json, depth: int = 0) -> None:
        if depth > 32:
            raise ValueError("schema too deep")
        if isinstance(value, dict):
            for key, item in value.items():
                if key in {"$id", "$anchor"}:
                    raise ValueError("schema rebasing is unsupported")
                if key == "$schema" and item != "https://json-schema.org/draft/2020-12/schema":
                    raise ValueError("only Draft 2020-12 is supported")
                if key in {"$dynamicRef", "$recursiveRef"}:
                    raise ValueError("dynamic references unsupported")
                if key == "$ref" and (not isinstance(item, str) or not item.startswith("#/$defs/")):
                    raise ValueError("only local definition references supported")
                if key == "$ref":
                    target = schema
                    try:
                        for part in item[2:].split("/"):
                            target = target[part.replace("~1", "/").replace("~0", "~")]
                    except (KeyError, TypeError) as exc:
                        raise ValueError("unresolved local schema reference") from exc
                walk(item, depth + 1)
        elif isinstance(value, list):
            for item in value:
                walk(item, depth + 1)

    walk(schema)
    Draft202012Validator.check_schema(schema)


def validate(schema: dict[str, Json], value: Json, code: str) -> None:
    try:
        canonical(value)
        Draft202012Validator(schema).validate(value)
    except (ValidationError, TypeError, ValueError, RecursionError) as exc:
        raise CoreError(code) from exc


@dataclass(frozen=True)
class Tool:
    name: str
    description: str
    function: Callable[..., Any]
    input_schema: dict[str, Json]
    version: str = "1"
    effect: Effect = Effect.READ
    permissions: frozenset[str] = frozenset()
    output_schema: dict[str, Json] | None = None
    semantic: Callable[[dict[str, Json]], None] | None = None
    timeout: float = 30

    def __post_init__(self) -> None:
        import re

        if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{0,63}", self.name):
            raise ValueError("invalid tool name")
        if not self.version or self.timeout <= 0:
            raise ValueError("version and positive timeout required")
        check_schema(self.input_schema)
        if self.input_schema.get("type") != "object":
            raise ValueError("arguments schema must be an object")
        if self.output_schema is not None:
            check_schema(self.output_schema)

    @classmethod
    def from_callable(
        cls,
        function: Callable[..., Any],
        *,
        name: str | None = None,
        description: str | None = None,
        version: str = "1",
        effect: Effect = Effect.READ,
        permissions: frozenset[str] = frozenset(),
        semantic: Callable[[dict[str, Json]], None] | None = None,
        timeout: float = 30,
    ) -> Tool:
        hints = get_type_hints(function)
        fields: dict[str, Any] = {}
        for param in inspect.signature(function).parameters.values():
            if param.kind not in {param.POSITIONAL_OR_KEYWORD, param.KEYWORD_ONLY}:
                raise ValueError("only named parameters supported")
            if param.name not in hints:
                raise ValueError("all parameters require annotations")
            default = ... if param.default is param.empty else param.default
            fields[param.name] = (hints[param.name], default)
        arguments = create_model(
            "ToolArguments",
            __config__=ConfigDict(extra="forbid", strict=True),
            **fields,
        )

        def invoke(**kwargs: Any) -> Any:
            parsed = arguments.model_validate(kwargs, strict=True)
            return function(**parsed.model_dump())

        # Keep coroutine classification so async work stays on the event loop.
        target = function if inspect.iscoroutinefunction(function) else invoke
        return cls(
            name=name or function.__name__,
            description=description or inspect.getdoc(function) or "",
            function=target,
            input_schema=arguments.model_json_schema(),
            version=version,
            effect=effect,
            permissions=permissions,
            semantic=semantic,
            timeout=timeout,
        )

    @property
    def declaration(self) -> dict[str, Json]:
        return {"name": self.name, "description": self.description, "parameters": self.input_schema}

    @property
    def manifest(self) -> str:
        return digest(
            {
                **self.declaration,
                "version": self.version,
                "effect": self.effect,
                "permissions": sorted(self.permissions),
                "output": self.output_schema,
                "timeout": self.timeout,
            }
        )

    def validate(self, arguments: dict[str, Json]) -> None:
        validate(self.input_schema, arguments, "invalid_arguments")
        if self.semantic is not None:
            try:
                self.semantic(arguments)
            except Exception as exc:
                raise CoreError("semantic_rejection") from exc


class Registry:
    def __init__(self, tools: tuple[Tool, ...] = ()):
        self._tools: dict[str, Tool] = {}
        for tool in tools:
            self.register(tool)

    def register(self, tool: Tool) -> None:
        if tool.name in self._tools:
            raise ValueError("duplicate tool name")
        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool:
        try:
            return self._tools[name]
        except KeyError as exc:
            raise CoreError("unknown_tool") from exc

    def all(self) -> tuple[Tool, ...]:
        return tuple(self._tools[name] for name in sorted(self._tools))
