"""Text and client function calls for the OpenAI Chat Completions contract."""

from __future__ import annotations

from collections.abc import AsyncGenerator

from pydantic import ValidationError

from agent_core.contracts import (
    Call,
    CoreError,
    Json,
    ModelDelta,
    Request,
    Response,
    Usage,
    canonical,
)

from .http import Capabilities, Transport, parse_arguments, usage_count
from .streaming import stream


class OpenAIChatModel:
    capabilities = Capabilities(native_output_schema=True, token_deltas=True)

    def __init__(
        self,
        model: str,
        api_key: str,
        *,
        transport: Transport | None = None,
        streaming: bool = False,
        endpoint: str = "https://api.openai.com/v1/chat/completions",
    ):
        if not api_key or not model:
            raise CoreError("provider_configuration")
        self.streaming = streaming
        self.model = model
        self._key = api_key
        self.endpoint = endpoint
        self.transport = transport or Transport()
        self.identity = "openai-chat:" + endpoint + ":" + model

    def encode(self, request: Request) -> dict[str, Json]:
        messages = []
        for message in request.messages:
            if message.metadata:
                if message.metadata.get("adapter") != self.identity:
                    raise CoreError("provider_metadata")
                messages.append(message.metadata["message"])
                continue
            encoded: dict[str, Json] = {"role": message.role, "content": message.content}
            if message.calls:
                encoded["tool_calls"] = [
                    {
                        "id": c.id,
                        "type": "function",
                        "function": {"name": c.name, "arguments": canonical(c.arguments)},
                    }
                    for c in message.calls
                ]
            if message.call_id is not None:
                encoded["tool_call_id"] = message.call_id
            messages.append(encoded)
        payload: dict[str, Json] = {
            "model": self.model,
            "messages": messages,
            "max_completion_tokens": request.max_output_tokens,
            "stream": False,
        }
        if request.tools:
            payload["tools"] = [{"type": "function", "function": tool} for tool in request.tools]
        if request.output_schema is not None:
            payload["response_format"] = {
                "type": "json_schema",
                "json_schema": {
                    "name": "agent_result",
                    "schema": request.output_schema,
                    "strict": True,
                },
            }
        return payload

    def decode(self, payload: dict[str, Json]) -> Response:
        try:
            choices = payload["choices"]
            if len(choices) != 1:
                raise ValueError("one choice required")
            choice = choices[0]
            message = choice["message"]
            if message.get("role") != "assistant":
                raise ValueError("assistant message required")
            # Unknown message fields may carry replay semantics we do not implement.
            if set(message) - {"role", "content", "tool_calls", "refusal", "annotations"}:
                raise ValueError("unsupported message content")
            text = message.get("content")
            text = "" if text is None else text
            if not isinstance(text, str):
                raise ValueError("text-only adapter")
            finish = choice["finish_reason"]
            if finish not in {"stop", "tool_calls"}:
                raise ValueError("incomplete response")
            refusal = message.get("refusal")
            if refusal is not None and not isinstance(refusal, str):
                raise ValueError("invalid refusal")
            normalized = []
            for call in message.get("tool_calls") or []:
                if call.get("type") != "function":
                    raise ValueError("unsupported call kind")
                normalized.append(
                    Call(
                        id=call["id"],
                        name=call["function"]["name"],
                        arguments=parse_arguments(call["function"]["arguments"]),
                    )
                )
            usage = payload.get("usage")
            usage = {} if usage is None else usage
            if not isinstance(usage, dict):
                raise ValueError("invalid usage")
            return Response(
                text=text,
                calls=tuple(normalized),
                finish="refusal" if message.get("refusal") else finish,
                usage=Usage(
                    input_tokens=usage_count(usage.get("prompt_tokens")),
                    output_tokens=usage_count(usage.get("completion_tokens")),
                ),
                metadata={
                    "adapter": self.identity,
                    "message": message,
                    "provider": {
                        key: payload[key]
                        for key in ("id", "model", "created", "system_fingerprint", "usage")
                        if key in payload
                    },
                },
            )
        except (
            AttributeError,
            KeyError,
            IndexError,
            TypeError,
            ValueError,
            ValidationError,
        ) as exc:
            raise CoreError("provider_response") from exc

    def stream(self, request: Request) -> AsyncGenerator[ModelDelta, None]:
        return stream(self, request, anthropic=False)

    async def complete(self, request: Request) -> Response:
        if self.streaming:
            response = None
            async for delta in self.stream(request):
                if delta.response is not None:
                    response = delta.response
            if response is None:
                raise CoreError("provider_response")
            return response
        payload = await self.transport.post(
            self.endpoint,
            {"Authorization": "Bearer " + self._key},
            self.encode(request),
        )
        return self.decode(payload)
