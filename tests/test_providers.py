import json

import httpx
import pytest

from agent_core import Call, CoreError, Message, Registry, Request, Runtime, Status
from agent_core.providers.anthropic import AnthropicModel
from agent_core.providers.http import Transport, parse_arguments
from agent_core.providers.openai_chat import OpenAIChatModel


def request(messages=None, output_schema=None):
    return Request(
        run_id="r",
        turn=0,
        messages=messages
        or (Message(role="system", content="rules"), Message(role="user", content="task")),
        tools=({"name": "lookup", "description": "lookup", "parameters": {"type": "object"}},),
        max_output_tokens=100,
        output_schema=output_schema,
    )


def openai_reply(finish="tool_calls"):
    return {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": "checking",
                    "tool_calls": [
                        {
                            "id": "c1",
                            "type": "function",
                            "function": {"name": "lookup", "arguments": '{"x":1}'},
                        }
                    ],
                },
                "finish_reason": finish,
            }
        ],
        "usage": {"prompt_tokens": 8, "completion_tokens": 3},
    }


def anthropic_reply(stop="tool_use"):
    return {
        "role": "assistant",
        "type": "message",
        "stop_reason": stop,
        "content": [
            {"type": "thinking", "thinking": "opaque", "signature": "original-signature"},
            {"type": "text", "text": "checking"},
            {"type": "tool_use", "id": "c1", "name": "lookup", "input": {"x": 1}},
            {"type": "tool_use", "id": "c2", "name": "lookup", "input": {"x": 2}},
        ],
        "usage": {"input_tokens": 8, "output_tokens": 3},
    }


@pytest.mark.parametrize("kind", ["openai", "anthropic"])
async def test_transport_and_round_trip_distinct_message_contracts(kind):
    seen = []
    payload = openai_reply() if kind == "openai" else anthropic_reply()

    def handler(req):
        seen.append(json.loads(req.content))
        assert (
            ("Authorization" in req.headers)
            if kind == "openai"
            else (req.headers["anthropic-version"] == "2023-06-01")
        )
        return httpx.Response(200, json=payload)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        model = (OpenAIChatModel if kind == "openai" else AnthropicModel)(
            "fixture-model", "fixture-secret", transport=Transport(client=client)
        )
        response = await model.complete(request())
        assert response.calls[0].arguments == {"x": 1}
        assert response.usage.total == 11
        messages = (
            request().messages
            + (
                Message(
                    role="assistant",
                    content=response.text,
                    calls=response.calls,
                    metadata=response.metadata,
                ),
            )
            + tuple(
                Message(role="tool", content='{"ok":true}', call_id=c.id) for c in response.calls
            )
        )
        replay = model.encode(request(messages))
        if kind == "openai":
            assert replay["messages"][2] == payload["choices"][0]["message"]
            assert replay["messages"][3]["tool_call_id"] == "c1"
            assert "system" not in replay
        else:
            assert replay["messages"][1]["content"] == payload["content"]
            results = replay["messages"][2]["content"]
            assert [b["tool_use_id"] for b in results] == ["c1", "c2"]
            assert replay["system"] == "rules"
        assert "fixture-secret" not in json.dumps(replay)


@pytest.mark.parametrize(
    "status,code,retryable",
    [
        (401, "provider_auth", False),
        (403, "provider_auth", False),
        (429, "provider_rate_limit", True),
        (503, "provider_unavailable", True),
        (302, "provider_response", False),
        (400, "provider_response", False),
    ],
)
async def test_http_error_classification_no_retry(status, code, retryable):
    attempts = []

    def handler(req):
        attempts.append(1)
        return httpx.Response(status, text="private diagnostics")

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        model = OpenAIChatModel("fixture", "secret", transport=Transport(client=client))
        with pytest.raises(CoreError) as raised:
            await model.complete(request())
        assert raised.value.code == code and raised.value.retryable == retryable
        assert len(attempts) == 1 and "private" not in str(raised.value)


@pytest.mark.parametrize("kind", ["openai", "anthropic"])
@pytest.mark.parametrize("broken", ["partial", "unknown", "missing", "duplicate", "unknown_usage"])
def test_provider_rejects_incomplete_or_unknown_shapes(kind, broken):
    model = (OpenAIChatModel if kind == "openai" else AnthropicModel)("fixture", "secret")
    payload = openai_reply() if kind == "openai" else anthropic_reply()
    if kind == "openai":
        if broken == "partial":
            payload["choices"][0]["finish_reason"] = "length"
        if broken == "unknown":
            payload["choices"][0]["message"]["audio"] = {}
        if broken == "missing":
            del payload["choices"]
        if broken == "duplicate":
            payload["choices"][0]["message"]["tool_calls"] *= 2
    else:
        if broken == "partial":
            payload["stop_reason"] = "max_tokens"
        if broken == "unknown":
            payload["content"].append({"type": "server_tool_use"})
        if broken == "missing":
            del payload["content"]
        if broken == "duplicate":
            payload["content"][-1]["id"] = "c1"
    if broken == "unknown_usage":
        del payload["usage"]
        assert model.decode(payload).usage.total is None
    else:
        with pytest.raises(CoreError, match="provider_response"):
            model.decode(payload)


@pytest.mark.parametrize("arguments", ['{"x":1,"x":2}', "[1,2]", '{"x":NaN}', '{"x":', None])
def test_argument_parser_rejects_ambiguous_json(arguments):
    with pytest.raises(CoreError):
        parse_arguments(arguments)


@pytest.mark.parametrize("body", [b'{"choices":', b"[]", b"x" * 200])
async def test_http_partial_and_bounded_response(body):
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(lambda req: httpx.Response(200, content=body))
    ) as client:
        with pytest.raises(CoreError):
            await Transport(client=client, response_bytes=128).post(
                "https://fixture.example", {}, {}
            )


async def test_transport_disconnect_and_https_required():
    def handler(req):
        raise httpx.ReadError("lost response")

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        transport = Transport(client=client)
        with pytest.raises(CoreError, match="provider_transport"):
            await transport.post("https://fixture.example", {}, {})
        with pytest.raises(CoreError, match="provider_configuration"):
            await transport.post("http://fixture.example", {}, {})


def test_output_schema_and_metadata_isolation():
    schema = {
        "type": "object",
        "properties": {"x": {"type": "integer"}},
        "required": ["x"],
        "additionalProperties": False,
    }
    o = OpenAIChatModel("fixture", "secret")
    a = AnthropicModel("fixture", "secret")
    assert (
        o.encode(request(output_schema=schema))["response_format"]["json_schema"]["schema"]
        == schema
    )
    assert "final answer must be JSON" in a.encode(request(output_schema=schema))["system"]
    bad = request((Message(role="assistant", metadata={"adapter": "foreign"}),))
    for model in [o, a]:
        with pytest.raises(CoreError, match="provider_metadata"):
            model.encode(bad)


@pytest.mark.parametrize("kind", ["openai", "anthropic"])
async def test_provider_final_through_runtime(kind, store):
    payload = (
        {
            "choices": [
                {"message": {"role": "assistant", "content": "done"}, "finish_reason": "stop"}
            ]
        }
        if kind == "openai"
        else {
            "role": "assistant",
            "type": "message",
            "stop_reason": "end_turn",
            "content": [{"type": "text", "text": "done"}],
        }
    )
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(lambda req: httpx.Response(200, json=payload))
    ) as client:
        model = (OpenAIChatModel if kind == "openai" else AnthropicModel)(
            "fixture", "secret", transport=Transport(client=client)
        )
        run = await Runtime(model, Registry(), store).run("respond")
        assert run.status == Status.COMPLETED and run.output == "done"


@pytest.mark.parametrize("mutation", ["choices", "role", "content", "kind"])
def test_openai_rejects_unsupported_complete_content(mutation):
    model = OpenAIChatModel("fixture", "secret")
    payload = openai_reply()
    if mutation == "choices":
        payload["choices"] = []
    elif mutation == "role":
        payload["choices"][0]["message"]["role"] = "user"
    elif mutation == "content":
        payload["choices"][0]["message"]["content"] = [{"type": "image"}]
    else:
        payload["choices"][0]["message"]["tool_calls"][0]["type"] = "custom"
    with pytest.raises(CoreError, match="provider_response"):
        model.decode(payload)


def test_provider_refusal_and_native_assistant_encoding():
    model = OpenAIChatModel("fixture", "secret")
    reply = {
        "choices": [
            {
                "message": {"role": "assistant", "content": None, "refusal": "declined"},
                "finish_reason": "stop",
            }
        ]
    }
    assert model.decode(reply).finish == "refusal"
    messages = request().messages + (
        Message(role="assistant", calls=(Call(id="c", name="lookup", arguments={"x": 1}),)),
        Message(role="tool", content="1", call_id="c"),
    )
    encoded = model.encode(request(messages))
    assert encoded["messages"][2]["tool_calls"][0]["function"]["arguments"] == '{"x":1}'
    anthropic = AnthropicModel("fixture", "secret")
    assert anthropic.encode(request(messages))["messages"][1]["content"][0]["type"] == "tool_use"
    assert (
        anthropic.decode(
            {"role": "assistant", "type": "message", "content": [], "stop_reason": "refusal"}
        ).finish
        == "refusal"
    )


@pytest.mark.parametrize("factory", [OpenAIChatModel, AnthropicModel])
def test_provider_empty_configuration_rejected(factory):
    with pytest.raises(CoreError, match="provider_configuration"):
        factory("", "secret")


@pytest.mark.parametrize("content", ["not-blocks", [{"type": "text", "text": 3}]])
def test_anthropic_text_block_validation(content):
    model = AnthropicModel("fixture", "secret")
    with pytest.raises(CoreError, match="provider_response"):
        model.decode(
            {"role": "assistant", "type": "message", "stop_reason": "end_turn", "content": content}
        )


@pytest.mark.parametrize("timeout", [float("nan"), float("inf"), 0])
def test_transport_timeout_is_finite(timeout):
    with pytest.raises(ValueError):
        Transport(timeout=timeout)


async def test_transport_rejects_duplicate_json_fields_and_redirects():
    seen = []

    def handler(req):
        seen.append(str(req.url))
        if req.url.path == "/duplicate":
            return httpx.Response(200, content=b'{"usage":1,"usage":2}')
        return httpx.Response(307, headers={"location": "https://other.example/"})

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handler),
        follow_redirects=True,
    ) as client:
        for path in ["duplicate", "redirect"]:
            with pytest.raises(CoreError, match="provider_response"):
                await Transport(client=client).post("https://fixture.example/" + path, {}, {})
    assert len(seen) == 2
