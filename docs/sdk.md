# Python SDK and custom tools

The public entry points are exported from `agent_core`.
`Runtime.run` creates and drives a new run. Use `create` plus `resume` to retain
an ID before work starts. Use `store.load(id)` for a snapshot and
`store.operations(id)` for exact recorded calls and approvals.

`Tool.from_callable` generates an object schema from annotated named parameters.
It supports JSON-native scalar, list and dictionary arguments and defaults.
Positional-only parameters and variadics are rejected. Annotations do not allow
arbitrary Python object deserialization. For another JSON contract, instantiate
`Tool` with an explicit input schema and optional output schema.

```python
from agent_core import Effect, Tool

def check_name(arguments):
    name = arguments["name"]
    if "/" in name or "\\" in name or name in {".", ".."}:
        raise ValueError("basename required")

def save_note(name: str, text: str) -> str:
    # Your trusted storage implementation belongs here.
    return f"Accepted {name}: {len(text)} characters"

tool = Tool.from_callable(
    save_note, version="1", effect=Effect.WRITE,
    permissions=frozenset({"notes:write"}), semantic=check_name,
)
```

The example above returns an acceptance string; it does not write a file. See
`examples/approved_workspace.py` for an actual preconditioned write.

Schemas use Draft 2020-12, bounded size/depth and local `$defs` references.
External references, schema rebasing and other dialects are rejected. The
semantic validator receives an isolated JSON copy and changed values are rejected
before dispatch. It is pure trusted host code; it must not mutate arguments,
perform side effects or grant rights. A tool version identifies implementation
semantics. Bump it when behavior or semantic constraints change.

Synchronous callables run in threads; async callables run on the event loop.
A tool may declare a timeout. Any exception from a write after dispatch is
conservatively uncertain, including failures before its internal side effect.

To require structured final output, pass `output_schema` to `run` or `create`.
The runtime parses and validates final JSON; invalid output produces
`invalid_output`. This validates shape, not the truth of a model's answer.

Generated callable inputs undergo strict Pydantic validation before dispatch for
both sync and async callables, in addition to JSON Schema validation. Tool timeouts
must be positive and finite.

Use `with Store(path) as store:` for deterministic database cleanup, including
host exceptions. Keep MCP connection contexts open while any registered runtime
is running; see [MCP](mcp.md). For typed provisional deltas see [streaming](streaming.md).
