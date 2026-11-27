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
