"""Groq Chat profile reusing complete-envelope and SSE safety contracts."""

from __future__ import annotations

from agent_core.contracts import CoreError, Json, Request, Response, canonical

from .http import Capabilities, Transport
from .openai_chat import OpenAIChatModel

# Documented reasoning controls: gpt-oss accepts low|medium|high, Qwen 3.8 accepts none.
# Low effort keeps hidden reasoning from exhausting max_completion_tokens.
REASONING_EFFORT = {
    "openai/gpt-oss-20b": "low",
    "openai/gpt-oss-120b": "low",
    "qwen/qwen3.8-27b": "none",
}


class GroqModel(OpenAIChatModel):
    capabilities = Capabilities(token_deltas=True, native_output_schema=False)

    def __init__(
        self,
        model: str,
        api_key: str,
        *,
        transport: Transport | None = None,
        streaming: bool = False,
    ):
        super().__init__(
            model,
            api_key,
            transport=transport,
            streaming=streaming,
            endpoint="https://api.groq.com/openai/v1/chat/completions",
        )
        self.identity = "groq-chat:" + self.endpoint + ":" + model

    def encode(self, request: Request) -> dict[str, Json]:
        payload = super().encode(request.model_copy(update={"output_schema": None}))
        if request.output_schema is not None:
            instruction = (
                "Return final JSON matching this schema: "
                + canonical(request.output_schema)
                + ". Tool calls are allowed before the final JSON answer."
            )
            messages = payload["messages"]
            if messages and messages[0].get("role") == "system":
                messages[0] = {
                    **messages[0],
                    "content": messages[0]["content"] + "\n" + instruction,
                }
            else:
                messages.insert(0, {"role": "system", "content": instruction})
        # JSON-schema response_format is incompatible with Groq tools/streaming.
        # Host validation remains mandatory; no endpoint schema guarantee is claimed.
        payload["parallel_tool_calls"] = False
        # Reasoning controls are sent only to models documented to accept them; other
        # models receive neither parameter. Reasoning text is never requested back
        # because unknown message fields are rejected, not replayed.
        effort = REASONING_EFFORT.get(self.model)
        if effort is not None:
            payload["include_reasoning"] = False
            payload["reasoning_effort"] = effort
        return payload

    def repeats_usage(self, first: Json, second: Json) -> bool:
        """Groq may repeat the receipt in x_groq and a final usage chunk; counters must match."""
        if not isinstance(first, dict) or not isinstance(second, dict):
            return False
        counters = ("prompt_tokens", "completion_tokens", "total_tokens")
        known = tuple(first.get(name) for name in counters)
        return known[0] is not None and known == tuple(second.get(name) for name in counters)

    def normalize_stream_event(self, event: dict[str, Json]) -> dict[str, Json]:
        try:
            extra = event.get("x_groq")
            if extra is None:
                return event
            if not isinstance(extra, dict):
                raise ValueError("invalid Groq metadata")
            usage = extra.get("usage")
            if usage is None:
                return event
            if not isinstance(usage, dict):
                raise ValueError("invalid Groq usage")
            if event.get("usage") is not None and event["usage"] != usage:
                raise ValueError("conflicting usage receipts")
            return {**event, "usage": usage}
        except (TypeError, ValueError) as exc:
            raise CoreError("provider_response") from exc

    def stream_metadata(self, event: dict[str, Json]) -> dict[str, Json]:
        return {"x_groq": event["x_groq"]} if "x_groq" in event else {}

    def decode(self, payload: dict[str, Json]) -> Response:
        payload = self.normalize_stream_event(payload)
        response = super().decode(payload)
        metadata = {**response.metadata}
        metadata["provider"] = {**metadata["provider"], **self.stream_metadata(payload)}
        return response.model_copy(update={"metadata": metadata})
