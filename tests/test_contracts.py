import sqlite3

import pytest
from jsonschema.exceptions import SchemaError
from pydantic import ValidationError

from agent_core import CoreError, Registry, Response, Store, Tool
from agent_core.contracts import canonical
from agent_core.tools import check_schema


@pytest.mark.parametrize(
    "response",
    [
        {"finish": "length"},
        {"finish": "tool_calls"},
        {"calls": [{"id": "1", "name": "x", "arguments": {}}]},
        {"finish": "tool_calls", "calls": [{"id": "1", "name": "x", "arguments": {}}] * 2},
    ],
)
def test_incomplete_response_rejected(response):
    with pytest.raises(ValidationError):
        Response(**response)


@pytest.mark.parametrize(
    "schema",
    [
        {"$ref": "https://invalid.example/schema"},
        {"$dynamicRef": "#x"},
        {"type": "made-up"},
    ],
)
def test_schema_registration_rejects_untrusted_resolution(schema):
    with pytest.raises((ValueError, SchemaError)):
        check_schema(schema)


def test_canonical_non_finite_and_key_order():
    assert canonical({"b": 1, "a": 2}) == canonical({"a": 2, "b": 1})
    with pytest.raises(ValueError):
        canonical({"x": float("nan")})


def test_generated_schema_and_invalid_signatures():
    def required(x):
        return x

    def variadic(*x: int) -> int:
        return len(x)

    for function in [required, variadic]:
        with pytest.raises(ValueError):
            Tool.from_callable(function)

    def valid(x: int = 2) -> int:
        return x

    tool = Tool.from_callable(valid)
    assert tool.function() == 2
    assert tool.manifest == tool.manifest
    with pytest.raises(ValueError):
        Registry((tool, tool))
    with pytest.raises(ValueError):
        Tool("../x", "bad", valid, {"type": "object"})


def test_store_unknown_version_and_transaction_rollback(tmp_path):
    path = tmp_path / "version.sqlite"
    connection = sqlite3.connect(path)
    connection.execute("PRAGMA user_version=99")
    connection.close()
    with pytest.raises(CoreError, match="unsupported_store_version"):
        Store(path)
    store = Store(tmp_path / "good.sqlite")
    try:
        with pytest.raises(ValueError):
            with store.transaction():
                store.connection.execute("INSERT INTO sessions VALUES ('bad',1)")
                raise ValueError("rollback")
        assert store.connection.execute("SELECT count(*) FROM sessions").fetchone()[0] == 0
        with pytest.raises(CoreError, match="unknown_run"):
            store.load("unknown")
        with pytest.raises(CoreError, match="unknown_artifact"):
            store.read_artifact("unknown")
    finally:
        store.close()


@pytest.mark.parametrize(
    "schema",
    [
        {"$ref": "#/$defs/missing"},
        {"$id": "https://fixture.example/"},
        {"$schema": "http://json-schema.org/draft-07/schema#"},
    ],
)
def test_schema_dialect_and_reference_targets_checked_at_registration(schema):
    with pytest.raises(ValueError):
        check_schema(schema)


def test_local_definition_validation():
    from agent_core.tools import validate

    schema = {
        "type": "object",
        "properties": {"x": {"$ref": "#/$defs/number"}},
        "$defs": {"number": {"type": "integer"}},
    }
    check_schema(schema)
    validate(schema, {"x": 1}, "invalid")
    with pytest.raises(CoreError, match="invalid"):
        validate(schema, {"x": "bad"}, "invalid")


@pytest.mark.parametrize("timeout", [float("nan"), float("inf"), -1, 0])
def test_tool_timeout_must_be_finite(timeout):
    with pytest.raises(ValueError):
        Tool("bounded", "", lambda: None, {"type": "object"}, timeout=timeout)


async def test_semantic_mutation_rejected_before_dispatch(store):
    from agent_core import Call, Policy, Runtime
    from agent_core.models import ScriptedModel

    executed = []

    def mutate(arguments):
        arguments["nested"]["value"] = "changed"

    tool = Tool(
        "guarded",
        "",
        lambda **kwargs: executed.append(kwargs),
        {"type": "object"},
        semantic=mutate,
    )
    call = Call(id="one", name="guarded", arguments={"nested": {"value": "original"}})
    model = ScriptedModel(
        (
            Response(calls=(call,), finish="tool_calls"),
            Response(text="done"),
        )
    )
    runtime = Runtime(model, Registry((tool,)), store, Policy(allowed_tools=frozenset({"guarded"})))
    run = await runtime.run("exercise semantic admission")
    assert executed == []
    assert call.arguments == {"nested": {"value": "original"}}
    assert store.operations(run.id)[0].code == "semantic_rejection"
    assert all(event.kind != "tool.dispatched" for event in store.events(run.id))


@pytest.mark.parametrize("asynchronous", [False, True])
async def test_generated_strict_input_rejected_before_write_dispatch(store, asynchronous):
    from agent_core import Call, Effect, Policy, Runtime
    from agent_core.models import ScriptedModel

    executed = []

    def sync_write(value: int) -> int:
        executed.append(value)
        return value

    async def async_write(value: int) -> int:
        return sync_write(value)

    tool = Tool.from_callable(
        async_write if asynchronous else sync_write,
        name="write",
        effect=Effect.WRITE,
    )
    # JSON Schema accepts integral floating point values; strict Python int does not.
    model = ScriptedModel(
        (
            Response(
                calls=(Call(id="one", name="write", arguments={"value": 1.0}),), finish="tool_calls"
            ),
            Response(text="done"),
        )
    )
    runtime = Runtime(
        model,
        Registry((tool,)),
        store,
        Policy(allowed_tools=frozenset({"write"}), approve_writes=False),
    )
    run = await runtime.run("validate before dispatch")
    assert executed == []
    assert store.operations(run.id)[0].code == "invalid_arguments"
    assert all(event.kind != "tool.dispatched" for event in store.events(run.id))
