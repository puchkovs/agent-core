"""Text and client tools for the Anthropic Messages 2023-06-01 profile.

This explicitly selected profile is fixture-verified; no claim is made for newer
API versions or server tools. Opaque thinking blocks are preserved during replay.
"""

from __future__ import annotations

from agent_core.contracts import Call, CoreError, Json, Request, Response, Usage, canonical

from .http import Capabilities, Transport, usage_count


class AnthropicModel:
    capabilities = Capabilities()

    def __init__(
        self,
        model: str,
        api_key: str,
        *,
        transport: Transport | None = None,
        endpoint: str = "https://api.anthropic.com/v1/messages",
    ):
        if not model or not api_key:
            raise CoreError("provider_configuration")
        self.model = model
        self._key = api_key
        self.endpoint = endpoint
        self.transport = transport or Transport()
        self.identity = "anthropic-messages-2023-06-01:" + endpoint + ":" + model

    def encode(self, request: Request) -> dict[str, Json]:
        system = []
        messages: list[dict[str, Json]] = []
        for message in request.messages:
            if message.role == "system":
                system.append(message.content)
                continue
            if message.role == "tool":
                block = {
                    "type": "tool_result",
                    "tool_use_id": message.call_id,
                    "content": message.content,
                }
                # One immediately following user message holds the whole call batch.
                if (
                    messages
                    and messages[-1].get("role") == "user"
                    and isinstance(messages[-1]["content"], list)
                ):
                    messages[-1]["content"].append(block)
                else:
                    messages.append({"role": "user", "content": [block]})
                continue
            if message.metadata:
                if message.metadata.get("adapter") != self.identity:
                    raise CoreError("provider_metadata")
                blocks = message.metadata["content"]
            else:
                blocks = [{"type": "text", "text": message.content}] if message.content else []
                blocks += [
                    {"type": "tool_use", "id": c.id, "name": c.name, "input": c.arguments}
                    for c in message.calls
                ]
            messages.append({"role": message.role, "content": blocks})
        if request.output_schema is not None:
            system.append(
                "The final answer must be JSON matching this schema: "
                + canonical(request.output_schema)
            )
        return {
            "model": self.model,
            "system": "\n".join(system),
            "messages": messages,
            "max_tokens": request.max_output_tokens,
            "stream": False,
            "tools": [
                {
                    "name": t["name"],
                    "description": t["description"],
                    "input_schema": t["parameters"],
                }
                for t in request.tools
            ],
        }

    def decode(self, payload: dict[str, Json]) -> Response:
        try:
            if payload.get("role") != "assistant" or payload.get("type") != "message":
                raise ValueError("message envelope required")
            stop = payload["stop_reason"]
            if stop not in {"end_turn", "tool_use", "refusal"}:
                raise ValueError("incomplete or unsupported response")
            text = []
            calls = []
            blocks = payload["content"]
            if not isinstance(blocks, list):
                raise ValueError("blocks required")
            for block in blocks:
                kind = block["type"]
                if kind == "text":
                    if not isinstance(block["text"], str):
                        raise ValueError("invalid text")
                    text.append(block["text"])
                elif kind == "tool_use":
                    calls.append(Call(id=block["id"], name=block["name"], arguments=block["input"]))
                elif kind not in {"thinking", "redacted_thinking"}:
                    raise ValueError("unsupported block")
            usage = payload.get("usage")
            usage = {} if usage is None else usage
            if not isinstance(usage, dict):
                raise ValueError("invalid usage")
            input_tokens = usage_count(usage.get("input_tokens"))
            for field in ("cache_creation_input_tokens", "cache_read_input_tokens"):
                cached = usage_count(usage.get(field, 0))
                input_tokens = (
                    None if input_tokens is None or cached is None else input_tokens + cached
                )
            return Response(
                text="\n".join(text),
                calls=tuple(calls),
                finish={"end_turn": "stop", "tool_use": "tool_calls", "refusal": "refusal"}[stop],
                usage=Usage(
                    input_tokens=input_tokens, output_tokens=usage_count(usage.get("output_tokens"))
                ),
                metadata={
                    "adapter": self.identity,
                    "content": blocks,
                    "provider": {
                        key: payload[key] for key in ("id", "model", "usage") if key in payload
                    },
                },
            )
        except (AttributeError, KeyError, TypeError, ValueError) as exc:
            raise CoreError("provider_response") from exc

    async def complete(self, request: Request) -> Response:
        payload = await self.transport.post(
            self.endpoint,
            {"x-api-key": self._key, "anthropic-version": "2023-06-01"},
            self.encode(request),
        )
        return self.decode(payload)
