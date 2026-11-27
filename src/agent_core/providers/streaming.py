"""Native stream assembly with explicit provider terminal boundaries."""

from __future__ import annotations

import json
from collections.abc import AsyncGenerator
from typing import Any

from agent_core.contracts import CoreError, ModelDelta, Request

from .http import parse_arguments, unique_object


def string(value: Any) -> str:
    if not isinstance(value, str):
        raise ValueError("string fragment required")
    return value


def index(value: Any) -> int:
    if type(value) is not int or value < 0 or value > 1024:
        raise ValueError("invalid stream index")
    return value


async def stream(
    model: Any, request: Request, *, anthropic: bool
) -> AsyncGenerator[ModelDelta, None]:
    payload = model.encode(request)
    payload["stream"] = True
    headers = (
        {"x-api-key": model._key, "anthropic-version": "2023-06-01"}
        if anthropic
        else {"Authorization": "Bearer " + model._key}
    )
    if not anthropic:
        payload["stream_options"] = {"include_usage": True}
    message: dict[str, Any] = {"role": "assistant", "content": ""}
    envelope: dict[str, Any] = {}
    calls: dict[int, Any] = {}
    blocks: list[Any] = []
    arguments: dict[int, str] = {}
    active: set[int] = set()
    started = False
    finished = False
    terminal = False
    source = model.transport.stream(model.endpoint, headers, payload)
    try:
        async for frame in source:
            if terminal:
                raise ValueError("data after terminal")
            if not anthropic and frame.data == "[DONE]":
                if not finished:
                    raise ValueError("missing finish reason")
                terminal = True
                continue
            event = json.loads(frame.data, object_pairs_hook=unique_object)
            if not isinstance(event, dict):
                raise ValueError("event object required")
            if anthropic:
                kind = event["type"]
                if frame.event != kind:
                    raise ValueError("event type mismatch")
                if kind == "ping":
                    continue
                if kind == "message_start":
                    if started or event["message"]["content"] != []:
                        raise ValueError("invalid start")
                    envelope = event["message"]
                    started = True
                elif not started:
                    raise ValueError("missing message start")
                elif kind == "content_block_start":
                    i = index(event["index"])
                    if finished or i != len(blocks) or active:
                        raise ValueError("invalid block start")
                    block = event["content_block"]
                    if block["type"] not in {"text", "tool_use", "thinking", "redacted_thinking"}:
                        raise ValueError("unsupported block")
                    blocks.append(block)
                    active.add(i)
                    if block["type"] == "tool_use":
                        if block["input"] != {}:
                            raise ValueError("nonempty initial tool input")
                        arguments[i] = ""
                elif kind == "content_block_delta":
                    i = index(event["index"])
                    if i not in active or finished:
                        raise ValueError("inactive block")
                    delta = event["delta"]
                    block = blocks[i]
                    field = {
                        "text_delta": "text",
                        "thinking_delta": "thinking",
                        "signature_delta": "signature",
                        "input_json_delta": "partial_json",
                    }[delta["type"]]
                    fragment = string(delta[field])
                    expected = {
                        "text": "text",
                        "thinking": "thinking",
                        "signature": "thinking",
                        "partial_json": "tool_use",
                    }[field]
                    if block["type"] != expected:
                        raise ValueError("delta block mismatch")
                    if field == "partial_json":
                        arguments[i] += fragment
                        yield ModelDelta(kind="arguments", text=fragment, index=i)
                    else:
                        block[field] = string(block.get(field, "")) + fragment
                        if field == "text":
                            yield ModelDelta(kind="text", text=fragment, index=i)
                elif kind == "content_block_stop":
                    i = index(event["index"])
                    if i not in active:
                        raise ValueError("inactive block stop")
                    active.remove(i)
                    if i in arguments:
                        blocks[i]["input"] = parse_arguments(arguments[i] or "{}")
                elif kind == "message_delta":
                    if active or finished:
                        raise ValueError("invalid message finish")
                    envelope.update(event["delta"])
                    envelope.setdefault("usage", {}).update(event.get("usage", {}))
                    finished = True
                    yield ModelDelta(kind="usage", data=envelope.get("usage", {}))
                elif kind == "message_stop":
                    if not finished or active:
                        raise ValueError("incomplete message")
                    terminal = True
                    envelope["content"] = blocks
                else:
                    raise ValueError("unsupported event")
            else:
                if frame.event != "message":
                    raise ValueError("unsupported event")
                event = model.normalize_stream_event(event)
                for name, value in model.stream_metadata(event).items():
                    previous = envelope.get(name)
                    envelope[name] = (
                        {**previous, **value}
                        if isinstance(previous, dict) and isinstance(value, dict)
                        else value
                    )
                for key in ("id", "model", "created", "system_fingerprint"):
                    if key in event:
                        if key in envelope and envelope[key] != event[key]:
                            raise ValueError("changed stream identity")
                        envelope[key] = event[key]
                choices = event["choices"]
                if event.get("usage") is not None:
                    if "usage" not in envelope:
                        envelope["usage"] = event["usage"]
                        yield ModelDelta(kind="usage", data=event["usage"])
                    elif not model.repeats_usage(envelope["usage"], event["usage"]):
                        raise ValueError("duplicate usage")
                if choices == []:
                    if not finished or event.get("usage") is None:
                        raise ValueError("unexpected empty choices")
                    continue
                if len(choices) != 1 or index(choices[0]["index"]) != 0 or finished:
                    raise ValueError("invalid choice")
                choice = choices[0]
                delta = choice["delta"]
                if set(delta) - {"role", "content", "tool_calls", "refusal"}:
                    raise ValueError("unsupported delta")
                if delta.get("role", "assistant") != "assistant":
                    raise ValueError("invalid role")
                for field in ("content", "refusal"):
                    if delta.get(field) is not None:
                        fragment = string(delta[field])
                        message[field] = message.get(field, "") + fragment
                        if field == "content":
                            yield ModelDelta(kind="text", text=fragment)
                for call in delta.get("tool_calls") or []:
                    i = index(call["index"])
                    if i not in calls:
                        if i != len(calls):
                            raise ValueError("noncontiguous calls")
                        calls[i] = {
                            "id": "",
                            "type": "function",
                            "function": {"name": "", "arguments": ""},
                        }
                    target = calls[i]
                    if call.get("type", "function") != "function":
                        raise ValueError("unsupported call")
                    if "id" in call:
                        target["id"] += string(call["id"])
                    for field, fragment in call.get("function", {}).items():
                        if field not in {"name", "arguments"}:
                            raise ValueError("unsupported function field")
                        target["function"][field] += string(fragment)
                        if field == "arguments":
                            yield ModelDelta(kind="arguments", text=fragment, index=i)
                if choice.get("finish_reason") is not None:
                    finished = True
                    envelope["choices"] = [
                        {"message": message, "finish_reason": choice["finish_reason"]}
                    ]
                    if calls:
                        message["tool_calls"] = list(calls.values())
        if not terminal:
            raise ValueError("missing terminal event")
        yield ModelDelta(kind="response", response=model.decode(envelope))
    except (AttributeError, KeyError, IndexError, TypeError, ValueError, RecursionError) as exc:
        raise CoreError("provider_response") from exc
    finally:
        await source.aclose()
