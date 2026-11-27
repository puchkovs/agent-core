import ast
import asyncio
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from test_runtime import calls, make

from agent_core import (
    CoreError,
    Effect,
    Limits,
    Policy,
    Registry,
    Response,
    Runtime,
    Status,
    Tool,
    Usage,
)
from agent_core.scenarios import workspace
from agent_core.tools import check_schema


async def test_pinned_context_size_and_creation_bounds(store):
    runtime = make(store, [Response(text="never")], limits=Limits(context_bytes=128))
    with pytest.raises(CoreError, match="context_limit"):
        runtime.create("x" * 129)
    run = await runtime.run("small prompt")
    assert run.reason == "context_limit" and not runtime.model.requests


@pytest.mark.parametrize("failure", ["exception", "oversized", "refusal", "exhausted"])
async def test_model_boundary_fails_without_dispatch(store, failure):
    if failure == "exception":

        def fail(request):
            raise CoreError("provider_auth")

        steps = [fail]
        reason = "provider_auth"
    elif failure == "oversized":
        steps = [Response(text="x" * 500)]
        reason = "provider_response"
    elif failure == "refusal":
        steps = [Response(finish="refusal")]
        reason = "refusal"
    else:
        steps = []
        reason = "script_exhausted"
    runtime = make(store, steps, limits=Limits(response_bytes=128))
    run = await runtime.run("work")
    assert run.reason == reason and store.operations(run.id) == ()


async def test_token_exact_budget_stops_next_model_turn(store):
    def read() -> str:
        return "ok"

    response = calls(("read", {})).model_copy(
        update={"usage": Usage(input_tokens=6, output_tokens=4)}
    )
    runtime = make(
        store,
        [response, Response(text="unreachable")],
        [Tool.from_callable(read)],
        limits=Limits(tokens=10),
    )
    run = await runtime.run("work")
    assert run.reason == "token_limit" and run.tool_count == 1
    assert len(runtime.model.requests) == 1


async def test_approved_but_expired_before_dispatch(store, monkeypatch):
    def write() -> str:
        pytest.fail("expired approval executed")

    runtime = make(store, [calls(("write", {}))], [Tool.from_callable(write, effect=Effect.WRITE)])
    run = await runtime.run("write")
    op = store.operations(run.id)[0]
    runtime.approve(run.id, op.id, op.binding, actor="host")
    # Expiry moves independently of the much later run deadline.
    import agent_core.runtime as runtime_module

    real_clock = runtime_module.time.time
    monkeypatch.setattr(runtime_module.time, "time", lambda: real_clock() + 301)
    # Use a longer deadline to isolate approval expiration from run expiration.
    store.save(run.model_copy(update={"deadline": real_clock() + 1000}), "test.clock")
    assert (await runtime.resume(run.id)).reason == "approval_expired"


async def test_cancellation_during_model_request_and_direct_task_cancel(store):
    started = asyncio.Event()

    class WaitingModel:
        identity = "waiting"

        async def complete(self, request):
            started.set()
            await asyncio.sleep(60)
            return Response(text="late")

    runtime = Runtime(WaitingModel(), Registry(), store)
    run_id = runtime.create("work")
    task = asyncio.create_task(runtime.resume(run_id))
    await started.wait()
    runtime.cancel(run_id)
    assert (await task).status == Status.CANCELLED
    started.clear()
    run_id = runtime.create("work")
    task = asyncio.create_task(runtime.resume(run_id))
    await started.wait()
    task.cancel()
    assert (await task).status == Status.CANCELLED


async def test_deadline_before_model_and_read_task_cancel(store):
    runtime = make(store, [Response(text="late")])
    run_id = runtime.create("work")
    run = store.load(run_id)
    store.save(run.model_copy(update={"deadline": 0}), "test.deadline")
    assert (await runtime.resume(run_id)).reason == "deadline"
    started = asyncio.Event()

    async def read() -> str:
        started.set()
        await asyncio.sleep(60)
        return "late"

    runtime = make(store, [calls(("read", {}))], [Tool.from_callable(read)])
    task = asyncio.create_task(runtime.run("work"))
    await started.wait()
    task.cancel()
    assert (await task).status == Status.CANCELLED


async def test_cancel_race_at_dispatch_transaction(store, monkeypatch):
    def write() -> str:
        pytest.fail("cancelled admission")

    runtime = make(store, [calls(("write", {}))], [Tool.from_callable(write)])
    original = store.save

    def race(run, kind, operation=None, data=None):
        if kind == "tool.dispatched":
            store.cancel(run.id)
        return original(run, kind, operation, data)

    monkeypatch.setattr(store, "save", race)
    assert (await runtime.run("work")).status == Status.CANCELLED


async def test_output_and_argument_bounds_and_awaitable_callable(store):
    async def finish():
        return "ok"

    def factory() -> str:
        return finish()

    def huge() -> str:
        return "x" * 1024

    def invalid() -> str:
        return object()

    def echo(x: str) -> str:
        pytest.fail("oversized arguments")

    runtime = make(
        store,
        [
            calls(("echo", {"x": "x" * 50}), ("huge", {}), ("invalid", {}), ("factory", {})),
            Response(text="done"),
        ],
        [
            Tool.from_callable(echo),
            Tool.from_callable(huge),
            Tool.from_callable(invalid),
            Tool.from_callable(factory),
        ],
        limits=Limits(argument_bytes=32, artifact_bytes=256),
    )
    run = await runtime.run("work")
    assert run.status == Status.COMPLETED
    ops = store.operations(run.id)
    assert [o.code for o in ops] == ["invalid_arguments", "output_limit", "invalid_output", None]


async def test_changed_configuration_before_first_drive(store):
    runtime = make(store, [Response(text="unused")])
    run_id = runtime.create("work")
    runtime.policy = Policy(scope="new")
    assert (await runtime.resume(run_id)).reason == "binding_changed"


def test_store_invalid_transition_event_ranges_and_artifact_slices(store):
    runtime = make(store, [Response(text="done")])
    run_id = runtime.create("task")
    with pytest.raises(CoreError, match="invalid_transition"):
        store.save(store.load(run_id).model_copy(update={"status": Status.COMPLETED}), "invalid")
    for limit in [0, 1001]:
        with pytest.raises(ValueError):
            store.events(run_id, limit=limit)
    for offset, limit in [(-1, 1), (0, 0), (0, 65537)]:
        with pytest.raises(ValueError):
            store.read_artifact("key", offset, limit)
    key = store.artifact("abcdef")
    assert store.read_artifact(key, 2, 2) == "cd"
    with pytest.raises(CoreError, match="unknown_run"):
        store.cancelled("absent")
    with pytest.raises(CoreError, match="invalid_actor"):
        store.decide(run_id, "op", "hash", "", True)
    with pytest.raises(CoreError, match="invalid_actor"):
        runtime.reconcile(run_id, "op", {}, actor="")
    assert os.stat(store.path).st_mode & 0o777 == 0o600


def test_schema_resource_bounds_and_tool_contracts():
    with pytest.raises(ValueError, match="large"):
        check_schema({"description": "x" * 65536})
    deep = {"type": "object"}
    for _ in range(40):
        deep = {"items": deep}
    with pytest.raises(ValueError, match="deep"):
        check_schema(deep)
    with pytest.raises(ValueError, match="version"):
        Tool("test", "test", lambda: 1, {"type": "object"}, version="")
    with pytest.raises(ValueError, match="object"):
        Tool("test", "test", lambda: 1, {"type": "array"})


def test_core_dependency_boundary():
    import agent_core

    root = Path(agent_core.__file__).parent
    for name in ["contracts", "policy", "tools", "store", "context", "runtime"]:
        tree = ast.parse((root / (name + ".py")).read_text())
        modules = [node.module or "" for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)]
        assert not any(
            m.startswith("agent_core.providers") or m.startswith("httpx") for m in modules
        )


async def test_workspace_symlink_rejected(store, tmp_path):
    root = tmp_path / "notes"
    runtime = workspace(store, root)
    outside = tmp_path / "outside.md"
    outside.write_text("untouched")
    (root / "plan.md").symlink_to(outside)
    run = await runtime.run("write")
    assert store.operations(run.id)[0].code == "semantic_rejection"
    assert outside.read_text() == "untouched"


@pytest.mark.parametrize(
    "boundary,count,status",
    [
        ("tool.dispatched", 0, "needs_reconciliation"),
        ("tool.completed", 1, "completed"),
        ("model.completed", 0, "completed"),
        ("model.started", 0, "completed"),
    ],
)
def test_real_process_death_and_restart(tmp_path, boundary, count, status):
    worker = Path(__file__).with_name("crash_worker.py")
    crashed = subprocess.run(
        [sys.executable, str(worker), str(tmp_path), boundary],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert crashed.returncode == 77, crashed.stderr
    effects = tmp_path / "effects.txt"
    assert (len(effects.read_text().splitlines()) if effects.exists() else 0) == count
    restarted = subprocess.run(
        [sys.executable, str(worker), str(tmp_path), "resume"],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert restarted.returncode == 0, restarted.stderr
    assert json.loads(restarted.stdout)["status"] == status
    if status == "completed":
        assert len(effects.read_text().splitlines()) == 1


async def test_preview_bound_includes_escaped_unicode_and_redaction(store):
    secret = 'private"\\key'

    def large() -> str:
        return secret + ('"\\\nЯ' * 1000)

    runtime = make(
        store,
        [calls(("large", {})), Response(text="done")],
        [Tool.from_callable(large)],
        limits=Limits(preview_bytes=128),
        secrets=(secret,),
    )
    run = await runtime.run("work")
    content = store.operations(run.id)[0].result
    assert len(content.encode()) <= 128
    envelope = json.loads(content)
    artifact = store.read_artifact(envelope["artifact"], limit=65536)
    assert secret not in artifact and "[REDACTED]" in artifact


async def test_known_credentials_cannot_enter_prompt_or_model_journal(store):
    runtime = make(store, [Response(text="credential-example")], secrets=("credential-example",))
    with pytest.raises(CoreError, match="secret_in_prompt"):
        runtime.create("credential-example")
    run = await runtime.run("work")
    assert run.reason == "secret_in_model_output"
    assert "credential-example" not in store.path.read_bytes().decode(errors="ignore")


async def test_failed_model_receipt_never_claims_zero_usage(store):
    def fail(request):
        raise CoreError("provider_transport")

    run = await make(store, [fail]).run("work")
    assert run.usage.total is None and not run.model_inflight


async def test_interrupted_model_usage_prevents_budgeted_retry(store):
    runtime = make(store, [Response(text="must not be requested")], limits=Limits(tokens=50))
    run_id = runtime.create("work")
    started = store.load(run_id).model_copy(
        update={"status": Status.RUNNING, "model_inflight": True}
    )
    store.save(started, "model.started")
    result = await runtime.resume(run_id)
    assert result.reason == "unknown_usage"
    assert runtime.model.requests == []


async def test_invalid_call_batch_also_checks_cancellation_between_calls(store, monkeypatch):
    runtime = make(store, [calls(("unknown", {}), ("also_unknown", {}))])
    original = store.save

    def cancel_after_first(run, kind, operation=None, data=None):
        original(run, kind, operation, data)
        if kind == "tool.completed":
            store.cancel(run.id)

    monkeypatch.setattr(store, "save", cancel_after_first)
    result = await runtime.run("malformed batch")
    assert result.status == Status.CANCELLED
    assert len(store.operations(result.id)) == 1


@pytest.mark.parametrize("boundary", ["model.started", "tool.dispatched"])
async def test_deadline_rechecked_in_admission_transaction(store, monkeypatch, boundary):
    def read() -> str:
        pytest.fail("expired dispatch executed")

    runtime = make(store, [calls(("read", {}))], [Tool.from_callable(read)])
    original = store.save

    def race(run, kind, operation=None, data=None):
        if kind == boundary:
            run = run.model_copy(update={"deadline": 0})
        return original(run, kind, operation, data)

    monkeypatch.setattr(store, "save", race)
    run = await runtime.run("work")
    assert run.reason == "deadline"
    assert run.tool_count == 0
    assert not any(event.kind == boundary for event in store.events(run.id))


async def test_cancel_at_model_admission_preserves_known_usage(store, monkeypatch):
    runtime = make(store, [Response(text="unreachable")])
    original = store.save

    def race(run, kind, operation=None, data=None):
        if kind == "model.started":
            store.cancel(run.id)
        return original(run, kind, operation, data)

    monkeypatch.setattr(store, "save", race)
    run = await runtime.run("work")
    assert run.status == Status.CANCELLED
    assert run.usage.total == 0
    assert runtime.model.requests == []


async def test_approval_expiry_rechecked_in_dispatch_transaction(store, monkeypatch):
    def write() -> str:
        pytest.fail("expired approval executed")

    runtime = make(store, [calls(("write", {}))], [Tool.from_callable(write, effect=Effect.WRITE)])
    run = await runtime.run("write")
    operation = store.operations(run.id)[0]
    runtime.approve(run.id, operation.id, operation.binding, actor="host")
    original = store.save

    def race(run, kind, operation=None, data=None):
        if kind == "tool.dispatched":
            operation = operation.model_copy(update={"expires_at": 0})
        return original(run, kind, operation, data)

    monkeypatch.setattr(store, "save", race)
    result = await runtime.resume(run.id)
    assert result.reason == "approval_expired"
    assert result.tool_count == 0
    assert store.operations(run.id)[0].status == "prepared"
