import json
import secrets

import httpx
import pytest
from test_providers import openai_reply, request

from agent_core import CoreError, Message, Policy, Registry, Runtime, Status, Tool
from agent_core.providers.groq import GroqModel
from agent_core.providers.http import Transport
from agent_core.providers.openai_chat import OpenAIChatModel


def test_groq_schema_fallback_and_openai_isolation():
    schema = {"type": "object"}
    req = request(output_schema=schema)
    groq = GroqModel("qwen/qwen3.8-27b", "fixture-key")
    encoded = groq.encode(req)
    assert "response_format" not in encoded
    assert '"type":"object"' in encoded["messages"][0]["content"]
    assert encoded["parallel_tool_calls"] is False
    assert encoded["include_reasoning"] is False
    assert encoded["reasoning_effort"] == "none"
    user_only = req.model_copy(update={"messages": (Message(role="user", content="work"),)})
    assert groq.encode(user_only)["messages"][0]["role"] == "system"
    assert not groq.capabilities.native_output_schema
    assert "response_format" in OpenAIChatModel("fixture", "fixture-key").encode(req)
    assert "fixture-key" not in json.dumps(encoded)
    foreign = groq.decode(openai_reply())
    assert foreign.metadata["adapter"].startswith("groq-chat:")


@pytest.mark.parametrize("extra", [[], {"usage": []}, {"usage": {"prompt_tokens": 9}}])
def test_groq_rejects_malformed_or_conflicting_usage(extra):
    payload = openai_reply()
    payload["x_groq"] = extra
    with pytest.raises(CoreError, match="provider_response"):
        GroqModel("fixture", "fixture-key").decode(payload)


@pytest.mark.parametrize("streaming", [False, True])
@pytest.mark.parametrize("nested_usage", [False, True])
async def test_groq_http_dynamic_tool_receipt_and_usage(store, streaming, nested_usage):
    receipt = secrets.token_hex(16)
    effects = []
    seen = []

    def calculate() -> dict:
        effects.append(1)
        return {"sum": 42, "receipt": receipt}

    def handler(req):
        payload = json.loads(req.content)
        seen.append(payload)
        assert str(req.url) == "https://api.groq.com/openai/v1/chat/completions"
        assert "response_format" not in payload
        assert payload["stream"] is streaming
        if len(seen) == 1:
            message = {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": "call",
                        "type": "function",
                        "function": {"name": "calculate", "arguments": "{}"},
                    },
                ],
            }
            finish = "tool_calls"
        else:
            observation = next(m["content"] for m in payload["messages"] if m["role"] == "tool")
            message = {"role": "assistant", "content": observation}
            finish = "stop"
        usage = {"prompt_tokens": 10, "completion_tokens": 5}
        metadata = {"id": "groq-request"}
        if not streaming:
            reply = {"choices": [{"message": message, "finish_reason": finish}], "x_groq": metadata}
            if nested_usage:
                metadata["usage"] = usage
            else:
                reply["usage"] = usage
            return httpx.Response(200, json=reply)
        delta = dict(message)
        if "tool_calls" in delta:
            delta["tool_calls"][0]["index"] = 0
        events = [
            {
                "choices": [{"index": 0, "delta": delta, "finish_reason": finish}],
                "x_groq": metadata,
            },
            {"choices": [], "x_groq": {"usage": usage}}
            if nested_usage
            else {"choices": [], "x_groq": metadata, "usage": usage},
        ]
        data = "".join("data: " + json.dumps(e) + "\n\n" for e in events) + "data: [DONE]\n\n"
        return httpx.Response(200, text=data, headers={"content-type": "text/event-stream"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        model = GroqModel(
            "qwen/qwen3.8-27b",
            "fixture-key",
            streaming=streaming,
            transport=Transport(client=client),
        )
        runtime = Runtime(
            model,
            Registry((Tool.from_callable(calculate),)),
            store,
            Policy(allowed_tools=frozenset({"calculate"})),
        )
        run = await runtime.run("calculate", output_schema={"type": "object"})
        assert run.status == Status.COMPLETED
        assert run.output == {"sum": 42, "receipt": receipt}
        assert effects == [1] and len(seen) == 2
        assert run.usage.total == 30
        assert run.groups[0][0].metadata["provider"]["x_groq"]["id"] == "groq-request"


@pytest.mark.parametrize("streaming", [False, True])
async def test_groq_rate_limit_never_retries_or_dispatches(store, streaming):
    calls = []

    def handler(req):
        calls.append(1)
        return httpx.Response(429, text="private diagnostics")

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        model = GroqModel(
            "fixture", "fixture-key", streaming=streaming, transport=Transport(client=client)
        )
        run = await Runtime(model, Registry(), store).run("work")
        assert run.reason == "provider_rate_limit"
        assert calls == [1] and store.operations(run.id) == ()


@pytest.mark.parametrize("streaming", [False, True])
async def test_groq_malformed_or_unterminated_response_never_dispatches(store, streaming):
    payload = openai_reply()
    if streaming:
        payload = {
            "choices": [
                {
                    "index": 0,
                    "delta": payload["choices"][0]["message"],
                    "finish_reason": "tool_calls",
                }
            ]
        }
        payload["choices"][0]["delta"]["tool_calls"][0]["index"] = 0
        response = httpx.Response(
            200,
            text="data: " + json.dumps(payload) + "\n\n",
            headers={"content-type": "text/event-stream"},
        )
    else:
        payload["choices"][0]["message"]["tool_calls"][0]["function"]["arguments"] = "{"
        response = httpx.Response(200, json=payload)
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda req: response)) as client:
        model = GroqModel(
            "fixture", "fixture-key", streaming=streaming, transport=Transport(client=client)
        )
        run = await Runtime(model, Registry(), store).run("work")
        assert run.reason == "provider_response"
        assert store.operations(run.id) == ()


@pytest.mark.parametrize(
    ("model", "effort"),
    [("openai/gpt-oss-20b", "low"), ("openai/gpt-oss-120b", "low"), ("qwen/qwen3.8-27b", "none")],
)
def test_groq_reasoning_controls_only_for_documented_models(model, effort):
    encoded = GroqModel(model, "fixture-key").encode(request())
    assert encoded["include_reasoning"] is False
    assert encoded["reasoning_effort"] == effort
    assert "response_format" not in encoded


@pytest.mark.parametrize("model", ["openai/gpt-oss-safeguard-20b", "llama-3.3-70b-versatile"])
def test_groq_omits_reasoning_controls_for_other_models(model):
    encoded = GroqModel(model, "fixture-key").encode(request())
    assert "include_reasoning" not in encoded and "reasoning_effort" not in encoded
    assert encoded["parallel_tool_calls"] is False
    assert encoded["max_completion_tokens"] == 100


def groq_stream(final_usage, trailing_usage):
    message = openai_reply()["choices"][0]["message"]
    message["tool_calls"][0]["index"] = 0
    events = [
        {
            "choices": [{"index": 0, "delta": message, "finish_reason": "tool_calls"}],
            "x_groq": {"id": "req", "usage": final_usage},
        },
        {"choices": [], "usage": trailing_usage},
    ]
    data = "".join("data: " + json.dumps(e) + "\n\n" for e in events) + "data: [DONE]\n\n"
    return httpx.Response(200, text=data, headers={"content-type": "text/event-stream"})


async def complete_groq(response, model_class=GroqModel):
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda req: response)) as client:
        model = model_class(
            "fixture", "fixture-key", streaming=True, transport=Transport(client=client)
        )
        return await model.complete(request())


async def test_groq_accepts_repeated_matching_stream_usage_once():
    receipt = {"prompt_tokens": 8, "completion_tokens": 3, "total_tokens": 11}
    response = groq_stream({**receipt, "total_time": 0.5}, {**receipt, "total_time": 0.6})
    result = await complete_groq(response)
    assert result.usage.total == 11
    assert result.metadata["provider"]["x_groq"]["usage"]["total_time"] == 0.5


@pytest.mark.parametrize(
    "trailing",
    [
        {"prompt_tokens": 8, "completion_tokens": 4, "total_tokens": 12},
        {"prompt_tokens": 8},
        {"total_tokens": 11},
    ],
)
async def test_groq_rejects_conflicting_or_partial_repeated_stream_usage(trailing):
    receipt = {"prompt_tokens": 8, "completion_tokens": 3, "total_tokens": 11}
    with pytest.raises(CoreError, match="provider_response"):
        await complete_groq(groq_stream(receipt, trailing))


async def test_groq_does_not_accept_receipt_without_prompt_counter_twice():
    with pytest.raises(CoreError, match="provider_response"):
        await complete_groq(groq_stream({"total_tokens": 11}, {"total_tokens": 11}))


async def test_openai_still_rejects_any_repeated_stream_usage():
    receipt = {"prompt_tokens": 8, "completion_tokens": 3, "total_tokens": 11}
    message = openai_reply()["choices"][0]["message"]
    message["tool_calls"][0]["index"] = 0
    events = [
        {
            "choices": [{"index": 0, "delta": message, "finish_reason": "tool_calls"}],
            "usage": receipt,
        },
        {"choices": [], "usage": receipt},
    ]
    data = "".join("data: " + json.dumps(e) + "\n\n" for e in events) + "data: [DONE]\n\n"
    response = httpx.Response(200, text=data, headers={"content-type": "text/event-stream"})
    with pytest.raises(CoreError, match="provider_response"):
        await complete_groq(response, OpenAIChatModel)


def test_groq_usage_repeat_requires_object_receipts():
    model = GroqModel("fixture", "fixture-key")
    receipt = {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2}
    assert model.repeats_usage(receipt, dict(receipt))
    assert not model.repeats_usage(receipt, [])
    assert not model.repeats_usage("receipt", receipt)
