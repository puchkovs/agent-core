import asyncio
import json

import httpx
import pytest
from test_providers import request

from agent_core import CoreError, Policy, Registry, Runtime, Status, Tool
from agent_core.providers.anthropic import AnthropicModel
from agent_core.providers.http import Transport
from agent_core.providers.openai_chat import OpenAIChatModel


def openai_events():
    return [
        {"choices": [{"index": 0, "delta": {"role": "assistant", "content": "checking"}}]},
        {
            "choices": [
                {
                    "index": 0,
                    "delta": {
                        "tool_calls": [
                            {
                                "index": 0,
                                "id": "a",
                                "type": "function",
                                "function": {"name": "lookup", "arguments": '{"x":'},
                            },
                            {
                                "index": 1,
                                "id": "b",
                                "type": "function",
                                "function": {"name": "lookup", "arguments": '{"x":2}'},
                            },
                        ]
                    },
                }
            ]
        },
        {
            "choices": [
                {
                    "index": 0,
                    "delta": {
                        "tool_calls": [
                            {"index": 0, "function": {"arguments": "1}"}},
                        ]
                    },
                    "finish_reason": "tool_calls",
                }
            ]
        },
        {"choices": [], "usage": {"prompt_tokens": 8, "completion_tokens": 3}},
        "[DONE]",
    ]


def anthropic_events():
    events = [
        {
            "type": "message_start",
            "message": {
                "id": "m",
                "model": "fixture",
                "role": "assistant",
                "type": "message",
                "content": [],
                "usage": {"input_tokens": 8, "output_tokens": 1},
            },
        },
        {"type": "ping"},
    ]
    for i, block, delta in [
        (
            0,
            {"type": "thinking", "thinking": "", "signature": ""},
            [
                {"type": "thinking_delta", "thinking": "opaque"},
                {"type": "signature_delta", "signature": "sig"},
            ],
        ),
        (1, {"type": "text", "text": ""}, [{"type": "text_delta", "text": "checking"}]),
        (
            2,
            {"type": "tool_use", "id": "a", "name": "lookup", "input": {}},
            [
                {"type": "input_json_delta", "partial_json": '{"x":'},
                {"type": "input_json_delta", "partial_json": "1}"},
            ],
        ),
        (
            3,
            {"type": "tool_use", "id": "b", "name": "lookup", "input": {}},
            [{"type": "input_json_delta", "partial_json": '{"x":2}'}],
        ),
    ]:
        events.append({"type": "content_block_start", "index": i, "content_block": block})
        events.extend({"type": "content_block_delta", "index": i, "delta": d} for d in delta)
        events.append({"type": "content_block_stop", "index": i})
    return events + [
        {
            "type": "message_delta",
            "delta": {"stop_reason": "tool_use"},
            "usage": {"output_tokens": 3},
        },
        {"type": "message_stop"},
    ]


def wire(events, anthropic):
    return b"".join(
        (("event: " + event["type"] + "\n") if anthropic else "").encode()
        + b"data: "
        + (event if isinstance(event, str) else json.dumps(event)).encode()
        + b"\n\n"
        for event in events
    )


class Body(httpx.AsyncByteStream):
    def __init__(self, data, fail=False):
        self.data, self.fail, self.closed = data, fail, False
        self.pulled = 0

    async def __aiter__(self):
        for i in range(0, len(self.data), 7):
            self.pulled += 1
            yield self.data[i : i + 7]
        if self.fail:
            raise httpx.ReadError("interrupted")

    async def aclose(self):
        self.closed = True


@pytest.mark.parametrize("anthropic", [False, True])
async def test_native_stream_multiple_tools_metadata_usage_and_cleanup(anthropic):
    body = Body(wire(anthropic_events() if anthropic else openai_events(), anthropic))
    seen = []

    def handler(req):
        seen.append(json.loads(req.content))
        return httpx.Response(200, stream=body, headers={"content-type": "text/event-stream"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        model = (AnthropicModel if anthropic else OpenAIChatModel)(
            "fixture",
            "secret",
            transport=Transport(client=client),
            streaming=True,
        )
        deltas = [d async for d in model.stream(request())]
        response = deltas[-1].response
        assert response.text == "checking"
        assert [c.arguments for c in response.calls] == [{"x": 1}, {"x": 2}]
        assert response.usage.total == 11
        assert any(d.kind == "arguments" for d in deltas)
        assert any(d.kind == "usage" for d in deltas)
        assert seen[0]["stream"] is True
        assert body.closed and not client.is_closed
        if anthropic:
            assert response.metadata["content"][0]["signature"] == "sig"


@pytest.mark.parametrize("anthropic", [False, True])
@pytest.mark.parametrize(
    "failure", ["missing_terminal", "disconnect", "malformed", "after_terminal"]
)
async def test_failed_native_stream_never_dispatches(store, anthropic, failure):
    events = anthropic_events() if anthropic else openai_events()
    if failure == "missing_terminal":
        events = events[:-1]
    elif failure == "malformed":
        events.insert(1, {"type": "unsupported"} if anthropic else {"choices": [{"index": -1}]})
    elif failure == "after_terminal":
        events += [events[0]]
    body = Body(wire(events, anthropic), fail=failure == "disconnect")
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda req: httpx.Response(
                200,
                stream=body,
                headers={"content-type": "text/event-stream"},
            )
        )
    ) as client:
        model = (AnthropicModel if anthropic else OpenAIChatModel)(
            "fixture",
            "secret",
            streaming=True,
            transport=Transport(client=client),
        )
        run = await Runtime(model, Registry(), store).run("work")
        assert run.status == Status.FAILED
        assert run.reason in {"provider_response", "provider_transport"}
        assert run.usage.total is None
        assert store.operations(run.id) == ()
        assert body.closed


@pytest.mark.parametrize("anthropic", [False, True])
async def test_runtime_native_stream_dispatches_only_complete_envelope(store, anthropic):
    executed = []

    def lookup(x: int) -> int:
        executed.append(x)
        return x

    requests = []

    def handler(req):
        requests.append(1)
        if len(requests) == 1:
            events = anthropic_events() if anthropic else openai_events()
        elif anthropic:
            events = [
                {
                    "type": "message_start",
                    "message": {"role": "assistant", "type": "message", "content": []},
                },
                {
                    "type": "content_block_start",
                    "index": 0,
                    "content_block": {"type": "text", "text": ""},
                },
                {
                    "type": "content_block_delta",
                    "index": 0,
                    "delta": {"type": "text_delta", "text": "done"},
                },
                {"type": "content_block_stop", "index": 0},
                {"type": "message_delta", "delta": {"stop_reason": "end_turn"}},
                {"type": "message_stop"},
            ]
        else:
            events = [
                {"choices": [{"index": 0, "delta": {"content": "done"}, "finish_reason": "stop"}]},
                "[DONE]",
            ]
        return httpx.Response(
            200, content=wire(events, anthropic), headers={"content-type": "text/event-stream"}
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        model = (AnthropicModel if anthropic else OpenAIChatModel)(
            "fixture",
            "secret",
            streaming=True,
            transport=Transport(client=client),
        )
        runtime = Runtime(
            model,
            Registry((Tool.from_callable(lookup),)),
            store,
            Policy(allowed_tools=frozenset({"lookup"})),
        )
        run_id = runtime.create("work")
        events = [e async for e in runtime.stream(run_id)]
        assert store.load(run_id).output == "done"
        assert executed == [1, 2]
        kinds = [e.kind for e in events]
        assert (
            kinds.index("model.delta")
            < kinds.index("model.completed")
            < kinds.index("tool.dispatched")
        )


async def test_native_transport_backpressure_close_and_cancellation():
    started = asyncio.Event()

    class Waiting(httpx.AsyncByteStream):
        closed = False

        async def __aiter__(self):
            started.set()
            await asyncio.Event().wait()
            yield b""

        async def aclose(self):
            self.closed = True

    body = Waiting()
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda req: httpx.Response(
                200,
                stream=body,
                headers={"content-type": "text/event-stream"},
            )
        )
    ) as client:
        stream = Transport(client=client).stream("https://fixture.example", {}, {})
        task = asyncio.create_task(anext(stream))
        await started.wait()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert body.closed


@pytest.mark.parametrize("anthropic", [False, True])
async def test_streaming_complete_sdk_and_early_close(anthropic):
    data = wire(anthropic_events() if anthropic else openai_events(), anthropic)
    bodies = []

    def handler(req):
        body = Body(data)
        bodies.append(body)
        return httpx.Response(200, stream=body, headers={"content-type": "text/event-stream"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        model = (AnthropicModel if anthropic else OpenAIChatModel)(
            "fixture",
            "secret",
            streaming=True,
            transport=Transport(client=client),
        )
        assert (await model.complete(request())).usage.total == 11
        stream = model.stream(request())
        await anext(stream)
        pulled = bodies[-1].pulled
        await stream.aclose()
        assert bodies[-1].closed and bodies[-1].pulled == pulled


@pytest.mark.parametrize(
    "status,code",
    [
        (401, "provider_auth"),
        (429, "provider_rate_limit"),
        (503, "provider_unavailable"),
        (302, "provider_response"),
        (200, "provider_response"),
    ],
)
async def test_native_http_error_classification(status, code):
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda req: httpx.Response(status, text="private diagnostics"),
        )
    ) as client:
        with pytest.raises(CoreError, match=code):
            _ = [
                f async for f in Transport(client=client).stream("https://fixture.example", {}, {})
            ]
        with pytest.raises(CoreError, match="provider_configuration"):
            _ = [f async for f in Transport(client=client).stream("http://fixture.example", {}, {})]


@pytest.mark.parametrize("case", range(18))
async def test_openai_stream_rejects_invalid_transitions(case):
    events = openai_events()
    bad = [
        "[DONE]",
        [],
        {"choices": []},
        {"choices": [{"index": 0, "delta": {"audio": {}}}]},
        {"choices": [{"index": 0, "delta": {"role": "user"}}]},
        {"choices": [{"index": 0, "delta": {"content": 1}}]},
        {"choices": [{"index": 0, "delta": {"tool_calls": [{"index": 2}]}}]},
        {"choices": [{"index": 0, "delta": {"tool_calls": [{"index": 0, "type": "custom"}]}}]},
        {
            "choices": [
                {"index": 0, "delta": {"tool_calls": [{"index": 0, "function": {"bad": "x"}}]}}
            ]
        },
    ]
    if case < len(bad):
        events.insert(0, bad[case])
    elif case == 9:
        events.insert(-1, events[-2])
    elif case == 10:
        events.insert(-2, events[0])
    elif case == 11:
        events[0]["id"] = "one"
        events[1]["id"] = "two"
    elif case == 12:
        events[0]["choices"][0]["index"] = True
    elif case == 13:
        events[2]["choices"][0]["finish_reason"] = "length"
    elif case == 14:
        events[2]["choices"][0]["delta"]["tool_calls"][0]["function"]["arguments"] = "bad"
    elif case == 15:
        events[1]["choices"][0]["delta"]["tool_calls"][1]["id"] = "a"
    elif case == 16:
        events[0] = {"choices": [{"index": 0, "delta": {"refusal": True}}]}
    else:
        events[-2]["usage"]["completion_tokens"] = -1
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda req: httpx.Response(
                200,
                content=wire(events, False),
                headers={"content-type": "text/event-stream"},
            )
        )
    ) as client:
        model = OpenAIChatModel("fixture", "secret", transport=Transport(client=client))
        with pytest.raises(CoreError, match="provider_response"):
            _ = [d async for d in model.stream(request())]


@pytest.mark.parametrize("case", range(15))
async def test_anthropic_stream_rejects_invalid_transitions(case):
    events = anthropic_events()
    if case == 0:
        events.insert(1, events[0])
    elif case == 1:
        events = events[1:]
    elif case == 2:
        events[2]["index"] = 1
    elif case == 3:
        events[2]["content_block"]["type"] = "server_tool_use"
    elif case == 4:
        events[3]["index"] = 99
    elif case == 5:
        events[3]["delta"] = {"type": "text_delta", "text": "wrong"}
    elif case == 6:
        events[5]["index"] = 99
    elif case == 7:
        events.insert(3, events[-2])
    elif case == 8:
        events.insert(-1, events[-2])
    elif case == 9:
        events = events[:-2] + [events[-1]]
    elif case == 10:
        events[9]["content_block"]["input"] = {"x": 1}
    elif case == 11:
        events.insert(
            -1,
            {
                "type": "content_block_start",
                "index": 4,
                "content_block": {"type": "text", "text": ""},
            },
        )
    elif case == 12:
        events[3]["delta"] = {"type": "unrecognized"}
    elif case == 13:
        events[-2]["delta"]["stop_reason"] = "max_tokens"
    else:
        events[10]["delta"]["partial_json"] = "bad"
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda req: httpx.Response(
                200,
                content=wire(events, True),
                headers={"content-type": "text/event-stream"},
            )
        )
    ) as client:
        model = AnthropicModel("fixture", "secret", transport=Transport(client=client))
        with pytest.raises(CoreError, match="provider_response"):
            _ = [d async for d in model.stream(request())]


@pytest.mark.parametrize("mode", ["cancel", "timeout", "disconnect"])
async def test_runtime_interrupted_stream_has_unknown_usage_and_no_tools(store, mode):
    from agent_core import Limits

    started = asyncio.Event()

    class Waiting(httpx.AsyncByteStream):
        closed = False

        async def __aiter__(self):
            yield wire(openai_events()[:2], False)
            started.set()
            if mode == "disconnect":
                raise httpx.ReadTimeout("private timeout")
            await asyncio.Event().wait()

        async def aclose(self):
            self.closed = True

    body = Waiting()
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda req: httpx.Response(
                200,
                stream=body,
                headers={"content-type": "text/event-stream"},
            )
        )
    ) as client:
        model = OpenAIChatModel(
            "fixture", "secret", streaming=True, transport=Transport(client=client)
        )
        runtime = Runtime(
            model, Registry(), store, limits=Limits(seconds=0.05 if mode == "timeout" else 10)
        )
        run_id = runtime.create("work")
        task = asyncio.create_task(runtime.resume(run_id))
        await started.wait()
        if mode == "cancel":
            runtime.cancel(run_id)
        result = await task
        assert (
            result.reason
            == {"cancel": "cancelled", "timeout": "deadline", "disconnect": "provider_transport"}[
                mode
            ]
        )
        assert result.usage.total is None
        assert store.operations(run_id) == ()
        assert body.closed


async def test_split_secret_suppresses_provisional_journal_and_limits(store):
    from agent_core import Limits

    events = [
        {"choices": [{"index": 0, "delta": {"content": "private-"}}]},
        {"choices": [{"index": 0, "delta": {"content": "value"}, "finish_reason": "stop"}]},
        "[DONE]",
    ]
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda req: httpx.Response(
                200,
                content=wire(events, False),
                headers={"content-type": "text/event-stream"},
            )
        )
    ) as client:
        model = OpenAIChatModel(
            "fixture", "secret", streaming=True, transport=Transport(client=client)
        )
        runtime = Runtime(model, Registry(), store, secrets=("private-value",))
        run = await runtime.run("work")
        assert run.reason == "secret_in_model_output"
        assert not any(e.kind == "model.delta" for e in store.events(run.id))
        runtime = Runtime(model, Registry(), store, limits=Limits(response_bytes=128))
        assert (await runtime.run("work")).reason == "provider_response"


async def test_native_stream_owned_transport_cleanup_and_wire_limit(monkeypatch):
    body = Body(wire(openai_events(), False))
    client = httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda req: httpx.Response(
                200,
                stream=body,
                headers={"content-type": "text/event-stream"},
            )
        )
    )
    monkeypatch.setattr(httpx, "AsyncClient", lambda **kwargs: client)
    with pytest.raises(CoreError, match="provider_response"):
        _ = [
            f async for f in Transport(response_bytes=128).stream("https://fixture.example", {}, {})
        ]
    assert client.is_closed and body.closed
