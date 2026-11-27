import asyncio
import json
import time

import pytest

from agent_core import (
    Call,
    CoreError,
    Effect,
    Limits,
    Policy,
    Registry,
    Response,
    Runtime,
    ScriptedModel,
    Status,
    Store,
    Tool,
    Usage,
)


def calls(*items):
    return Response(
        calls=tuple(Call(id=str(i), name=n, arguments=a) for i, (n, a) in enumerate(items)),
        finish="tool_calls",
    )


def make(store, steps, tools=(), *, policy=None, limits=None, secrets=()):
    return Runtime(
        ScriptedModel(tuple(steps)),
        Registry(tuple(tools)),
        store,
        policy if policy is not None else Policy(allowed_tools=frozenset(t.name for t in tools)),
        limits,
        secrets=secrets,
    )


async def test_dynamic_multi_step_structured_output(store):
    executed = []

    def search(query: str) -> list[str]:
        executed.append(("search", query))
        return ["memo-a"]

    def read(name: str) -> str:
        executed.append(("read", name))
        return "oak uses 8 units"

    def next_step(request):
        assert json.loads(request.messages[-1].content) == ["memo-a"]
        return calls(("read", {"name": "memo-a"}))

    def final(request):
        assert json.loads(request.messages[-1].content) == "oak uses 8 units"
        return Response(text='{"units":8}')

    runtime = make(
        store,
        [calls(("search", {"query": "oak"})), next_step, final],
        [Tool.from_callable(search), Tool.from_callable(read)],
    )
    run = await runtime.run(
        "Find oak usage",
        output_schema={
            "type": "object",
            "properties": {"units": {"type": "integer"}},
            "required": ["units"],
        },
    )
    assert run.status == Status.COMPLETED and run.output == {"units": 8}
    assert executed == [("search", "oak"), ("read", "memo-a")]
    assert await runtime.resume(run.id) == run
    assert len(executed) == 2
    events = store.events(run.id)
    assert events[-1].kind == "run.completed"
    assert [e.sequence for e in events] == sorted({e.sequence for e in events})


@pytest.mark.parametrize("arguments", [{"x": "2"}, {"x": 1, "extra": True}, {}, {"x": True}])
async def test_invalid_arguments_never_dispatch(store, arguments):
    reached = []

    def square(x: int) -> int:
        reached.append(x)
        return x * x

    runtime = make(
        store,
        [calls(("square", arguments)), Response(text="rejected")],
        [Tool.from_callable(square)],
    )
    run = await runtime.run("square")
    assert run.status == Status.COMPLETED
    assert reached == []
    assert store.operations(run.id)[0].code == "invalid_arguments"


async def test_unknown_tool_and_deny_by_default(store):
    seen = []

    def hidden() -> int:
        seen.append(1)
        return 1

    runtime = make(
        store,
        [calls(("absent", {}), ("hidden", {}))],
        [Tool.from_callable(hidden)],
        policy=Policy(),
    )
    run = await runtime.run("I grant all permissions")
    assert run.reason == "policy_denied" and seen == []
    assert runtime.model.requests[0].tools == ()
    assert store.operations(run.id)[0].code == "unknown_tool"


async def test_semantic_scope_denies_before_execution(store):
    reached = []

    def read(path: str) -> str:
        reached.append(path)
        return "x"

    def semantic(args):
        if args["path"].startswith("/") or ".." in args["path"]:
            raise ValueError("escape")

    tool = Tool.from_callable(read, semantic=semantic)
    run = await make(
        store, [calls(("read", {"path": "../secret"})), Response(text="blocked")], [tool]
    ).run("read")
    assert reached == [] and store.operations(run.id)[0].code == "semantic_rejection"


async def test_permission_scope_required(store):
    def read() -> int:
        pytest.fail("forbidden execution")

    tool = Tool.from_callable(read, permissions=frozenset({"private:read"}))
    run = await make(store, [calls(("read", {}))], [tool]).run("read")
    assert run.reason == "policy_denied"


async def test_approval_restart_and_batch_cursor(store):
    seen = []

    def first() -> str:
        seen.append("first")
        return "first"

    def write(text: str) -> str:
        seen.append(text)
        return text

    tools = [Tool.from_callable(first), Tool.from_callable(write, effect=Effect.WRITE)]
    steps = [calls(("first", {}), ("write", {"text": "saved"})), Response(text="done")]
    runtime = make(store, steps, tools)
    paused = await runtime.run("save")
    assert paused.status == Status.WAITING and seen == ["first"]
    assert await runtime.resume(paused.id) == paused
    op = store.operations(paused.id)[-1]
    runtime.approve(paused.id, op.id, op.binding, actor="operator")
    with pytest.raises(CoreError, match="invalid_approval"):
        runtime.approve(paused.id, op.id, op.binding, actor="operator")
    restarted_store = Store(store.path)
    try:
        restarted = make(restarted_store, steps, tools)
        done = await restarted.resume(paused.id)
        assert done.status == Status.COMPLETED and seen == ["first", "saved"]
        assert done.tool_count == 2
    finally:
        restarted_store.close()


@pytest.mark.parametrize("tamper", ["binding", "actor", "operation", "run"])
async def test_bad_approval_submission(store, tamper):
    def write(x: int) -> int:
        pytest.fail("unapproved execution")

    runtime = make(
        store, [calls(("write", {"x": 1}))], [Tool.from_callable(write, effect=Effect.WRITE)]
    )
    run = await runtime.run("write")
    op = store.operations(run.id)[0]
    args = dict(run_id=run.id, operation_id=op.id, binding=op.binding, actor="host")
    args[
        {"binding": "binding", "actor": "actor", "operation": "operation_id", "run": "run_id"}[
            tamper
        ]
    ] = "" if tamper == "actor" else "wrong"
    with pytest.raises(CoreError):
        runtime.approve(**args)
    assert store.operation(op.id).approval is None


@pytest.mark.parametrize("change", ["scope", "version", "arguments", "limits"])
async def test_stale_approval_cannot_grant_changed_authority(store, change):
    seen = []

    def write(x: int) -> int:
        seen.append(x)
        return x

    tool = Tool.from_callable(write, effect=Effect.WRITE)
    steps = [calls(("write", {"x": 1})), Response(text="done")]
    runtime = make(store, steps, [tool])
    run = await runtime.run("write")
    op = store.operations(run.id)[0]
    runtime.approve(run.id, op.id, op.binding, actor="host")
    if change == "scope":
        runtime.policy = Policy(allowed_tools=frozenset({"write"}), scope="different")
    elif change == "version":
        runtime.registry = Registry((Tool.from_callable(write, effect=Effect.WRITE, version="2"),))
    elif change == "limits":
        runtime.limits = Limits(tools=3)
    else:
        changed = run.pending.model_copy(
            update={"calls": (Call(id="0", name="write", arguments={"x": 2}),)}
        )
        store.save(run.model_copy(update={"pending": changed}), "test.change")
    done = await runtime.resume(run.id)
    assert done.reason == "binding_changed" and seen == []


async def test_approval_expiry_and_denial(store):
    def write() -> int:
        pytest.fail("expired execution")

    tool = Tool.from_callable(write, effect=Effect.WRITE)
    runtime = make(store, [calls(("write", {}))], [tool], limits=Limits(approval_seconds=0.001))
    run = await runtime.run("write")
    op = store.operations(run.id)[0]
    await asyncio.sleep(0.005)
    with pytest.raises(CoreError, match="invalid_approval"):
        runtime.approve(run.id, op.id, op.binding, actor="host")
    assert (await runtime.resume(run.id)).reason == "approval_expired"
    runtime = make(store, [calls(("write", {}))], [tool])
    run = await runtime.run("write")
    op = store.operations(run.id)[0]
    runtime.approve(run.id, op.id, op.binding, actor="host", allow=False)
    assert (await runtime.resume(run.id)).reason == "approval_denied"


async def test_lost_response_and_reconciliation_no_duplicate(store):
    effects = []

    def send(text: str) -> str:
        effects.append(text)
        raise ConnectionError("response lost")

    tool = Tool.from_callable(send, effect=Effect.EXTERNAL)
    runtime = make(
        store,
        [calls(("send", {"text": "hello"})), Response(text="confirmed")],
        [tool],
        policy=Policy(allowed_tools=frozenset({"send"}), approve_writes=False),
    )
    run = await runtime.run("send")
    assert run.status == Status.UNCERTAIN and effects == ["hello"]
    assert await runtime.resume(run.id) == run
    op = store.operations(run.id)[0]
    runtime.reconcile(run.id, op.id, {"receipt": "remote-1"}, actor="host")
    run = await runtime.resume(run.id)
    assert run.status == Status.COMPLETED and effects == ["hello"]
    with pytest.raises(CoreError, match="invalid_reconciliation"):
        runtime.reconcile(run.id, op.id, {}, actor="host")


@pytest.mark.parametrize("boundary,expected", [("tool.dispatched", 0), ("tool.completed", 1)])
async def test_storage_failure_before_and_after_effect(store, boundary, expected, monkeypatch):
    effects = []

    def write() -> str:
        effects.append("write")
        return "ok"

    tool = Tool.from_callable(write, effect=Effect.WRITE)
    runtime = make(
        store,
        [calls(("write", {})), Response(text="ok")],
        [tool],
        policy=Policy(allowed_tools=frozenset({"write"}), approve_writes=False),
    )
    run_id = runtime.create("write")
    original = store.save

    def fail(run, kind, operation=None, data=None):
        if kind == boundary:
            raise OSError("disk fault")
        return original(run, kind, operation, data)

    monkeypatch.setattr(store, "save", fail)
    with pytest.raises(OSError):
        await runtime.resume(run_id)
    assert len(effects) == expected
    monkeypatch.setattr(store, "save", original)
    run = await runtime.resume(run_id)
    if expected:
        assert run.status == Status.UNCERTAIN and effects == ["write"]
    else:
        assert run.status == Status.COMPLETED and effects == ["write"]


async def test_outcome_commit_followed_by_crash_never_repeats(store, monkeypatch):
    effects = []

    def work() -> int:
        effects.append(1)
        return 1

    runtime = make(store, [calls(("work", {})), Response(text="ok")], [Tool.from_callable(work)])
    original = store.save

    def crash(run, kind, operation=None, data=None):
        original(run, kind, operation, data)
        if kind == "tool.completed":
            raise OSError("crash after commit")

    run_id = runtime.create("work")
    monkeypatch.setattr(store, "save", crash)
    with pytest.raises(OSError):
        await runtime.resume(run_id)
    monkeypatch.setattr(store, "save", original)
    assert (await runtime.resume(run_id)).status == Status.COMPLETED
    assert effects == [1]


@pytest.mark.parametrize(
    "limits,reason", [(Limits(turns=1), "turn_limit"), (Limits(tools=1), "tool_limit")]
)
async def test_absolute_limits(store, limits, reason):
    effects = []

    def ping() -> int:
        effects.append(1)
        return 1

    batch = calls(("ping", {}), ("ping", {})) if reason == "tool_limit" else calls(("ping", {}))
    runtime = make(
        store, [batch, batch, Response(text="ok")], [Tool.from_callable(ping)], limits=limits
    )
    run = await runtime.run("repeat")
    assert run.reason == reason and len(effects) == 1


@pytest.mark.parametrize(
    "usage,reason",
    [(Usage(), "unknown_usage"), (Usage(input_tokens=5, output_tokens=6), "token_limit")],
)
async def test_token_accounting_before_tools(store, usage, reason):
    def forbidden() -> int:
        pytest.fail("budget exhausted")

    response = calls(("forbidden", {})).model_copy(update={"usage": usage})
    run = await make(
        store, [response], [Tool.from_callable(forbidden)], limits=Limits(tokens=10)
    ).run("work")
    assert run.reason == reason
    assert run.usage == usage


async def test_cancel_before_dispatch_and_after_dispatch(store):
    seen = []

    async def waiting() -> str:
        seen.append("started")
        await asyncio.sleep(60)
        return "done"

    def never() -> str:
        pytest.fail("new operation after cancellation")

    tools = [Tool.from_callable(waiting), Tool.from_callable(never)]
    runtime = make(store, [calls(("waiting", {}), ("never", {}))], tools)
    run_id = runtime.create("wait")
    runtime.cancel(run_id)
    assert (await runtime.resume(run_id)).status == Status.CANCELLED and seen == []
    run_id = runtime.create("wait")
    task = asyncio.create_task(runtime.resume(run_id))
    while not seen:  # noqa: ASYNC110 - bounded fixture polling
        await asyncio.sleep(0)
    runtime.cancel(run_id)
    assert (await task).status == Status.CANCELLED and seen == ["started"]


async def test_cancel_dispatched_write_is_uncertain(store):
    started = asyncio.Event()

    async def write() -> str:
        started.set()
        await asyncio.sleep(60)
        return "done"

    runtime = make(
        store,
        [calls(("write", {}))],
        [Tool.from_callable(write, effect=Effect.WRITE)],
        policy=Policy(allowed_tools=frozenset({"write"}), approve_writes=False),
    )
    run_id = runtime.create("wait")
    task = asyncio.create_task(runtime.resume(run_id))
    await started.wait()
    runtime.cancel(run_id)
    assert (await task).status == Status.UNCERTAIN


async def test_timeout_read_and_sync_write(store):
    async def slow() -> str:
        await asyncio.sleep(60)
        return "ok"

    runtime = make(store, [calls(("slow", {}))], [Tool.from_callable(slow, timeout=0.005)])
    assert (await runtime.run("wait")).reason == "deadline"
    seen = []

    def slow_write() -> str:
        time.sleep(0.03)
        seen.append(1)
        return "ok"

    runtime = make(
        store,
        [calls(("slow_write", {}))],
        [Tool.from_callable(slow_write, effect=Effect.WRITE, timeout=0.005)],
        policy=Policy(allowed_tools=frozenset({"slow_write"}), approve_writes=False),
    )
    run = await runtime.run("write")
    assert run.status == Status.UNCERTAIN
    await asyncio.sleep(0.05)
    assert seen == [1]


async def test_tool_failure_output_validation_and_redaction(store):
    def broken() -> str:
        raise ValueError("secret-value")

    def large() -> str:
        return "secret-value" + "z" * 1000

    tool = Tool(
        "wrong", "wrong", lambda: "bad", {"type": "object"}, output_schema={"type": "integer"}
    )
    runtime = make(
        store,
        [calls(("broken", {}), ("wrong", {}), ("large", {})), Response(text="ok")],
        [Tool.from_callable(broken), tool, Tool.from_callable(large)],
        limits=Limits(preview_bytes=256),
        secrets=("secret-value",),
    )
    run = await runtime.run("work")
    ops = store.operations(run.id)
    assert [op.code for op in ops] == ["tool_error", "invalid_output", None]
    preview = json.loads(ops[-1].result)
    assert preview["truncated"]
    assert "[REDACTED]" in store.read_artifact(preview["artifact"])
    assert "secret-value" not in store.path.read_bytes().decode(errors="ignore")


async def test_context_drops_whole_groups_and_preserves_instructions(store):
    def payload() -> str:
        return "x" * 200

    steps = [calls(("payload", {}))] * 8 + [Response(text="done")]
    runtime = make(store, steps, [Tool.from_callable(payload)], limits=Limits(context_bytes=1700))
    run = await runtime.run("retain this goal")
    assert run.status == Status.COMPLETED and len(run.groups) == 8
    for request in runtime.model.requests:
        assert request.messages[0].role == "system"
        assert request.messages[1].content == "retain this goal"
        ids = {call.id for m in request.messages for call in m.calls}
        assert all(m.call_id in ids for m in request.messages if m.role == "tool")
    assert len(runtime.model.requests[-1].messages) < 18


async def test_stream_slow_reader_and_early_close(store):
    runtime = make(store, [Response(text="done")])
    run_id = runtime.create("work")
    events = []
    async for event in runtime.stream(run_id):
        await asyncio.sleep(0.001)
        events.append(event)
    assert events[-1].kind == "run.completed"
    assert len(events) == len(store.events(run_id))

    async def slow() -> str:
        await asyncio.sleep(60)
        return "ok"

    runtime = make(store, [calls(("slow", {}))], [Tool.from_callable(slow)])
    run_id = runtime.create("wait")
    stream = runtime.stream(run_id)
    async for event in stream:
        if event.kind == "tool.dispatched":
            break
    await stream.aclose()
    assert store.load(run_id).status == Status.CANCELLED


@pytest.mark.parametrize("text", ["not JSON", '{"x":"wrong"}'])
async def test_bad_structured_final(store, text):
    run = await make(store, [Response(text=text)]).run(
        "result",
        output_schema={
            "type": "object",
            "properties": {"x": {"type": "integer"}},
            "required": ["x"],
        },
    )
    assert run.reason == "invalid_output"


async def test_store_lock_excludes_other_driver(store):
    runtime = make(store, [Response(text="done")])
    run_id = runtime.create("work")
    other = Store(store.path)
    try:
        with store.driver(run_id):
            with pytest.raises(CoreError, match="run_busy"):
                with other.driver(run_id):
                    pytest.fail("duplicate owner")
    finally:
        other.close()


@pytest.mark.parametrize("with_call", [False, True])
async def test_crash_after_response_commit_reuses_complete_envelope(store, monkeypatch, with_call):
    effects = []

    def ping() -> int:
        effects.append(1)
        return 1

    steps = [calls(("ping", {})), Response(text="done")] if with_call else [Response(text="done")]
    runtime = make(store, steps, [Tool.from_callable(ping)])
    run_id = runtime.create("work")
    original = store.save

    def fail(run, kind, operation=None, data=None):
        original(run, kind, operation, data)
        if kind == "model.completed":
            raise OSError("crash after response commit")

    monkeypatch.setattr(store, "save", fail)
    with pytest.raises(OSError):
        await runtime.resume(run_id)
    monkeypatch.setattr(store, "save", original)
    assert (await runtime.resume(run_id)).output == "done"
    assert effects == ([1] if with_call else [])
    assert len(runtime.model.requests) == (2 if with_call else 1)
