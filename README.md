# Agent Core

Agent Core is a local Python runtime for model-directed, multi-step tool use.
The host controls tools, permissions, approvals and budgets. SQLite records
admission and outcomes so interrupted writes are not blindly repeated.

**Version 0.1.0a1 — engineering candidate.** Offline contracts are tested. Live
endpoint verification remains a release gate. Native Python tools have process
privileges; this package does not provide an operating-system sandbox.

## What it provides

- A reusable sequential agent loop with pluggable model and native tool contracts.
- Generated tool schemas, argument validation and semantic resource checks.
- Deny-by-default permissions and operation-specific approval pauses.
- Persistent sessions, checkpoints, event cursors and explicit uncertain outcomes.
- Iteration, tool, elapsed time, reported token and serialized payload limits.
- Structured final-output validation and bounded tool previews with artifacts.
- A Python SDK, local CLI and three offline demonstrations.

The runtime contains no task-specific tool sequence. The selected model proposes
calls; host policy decides whether those calls can execute. Scripted examples
verify runtime behavior and are not language-model intelligence evaluations.

## Installation

Baseline: CPython 3.12 on Linux. Install from the restored checkout:

```sh
python3 -m venv .venv
. .venv/bin/activate
pip install --require-hashes -r requirements-dev.lock
pip install -e . --no-deps
make check
```

For runtime-only use: `pip install .`. Add `[providers]` for the HTTP adapters.
The distribution name is `agent-core-runtime`; the import namespace is
`agent_core`. Nothing is published to a package index as part of this candidate.

## Python quick start

```python
import asyncio
from agent_core import (
    Call, Policy, Registry, Response, Runtime, ScriptedModel, Store, Tool,
)

def add(left: int, right: int) -> int:
    """Add two integers."""
    return left + right

async def main():
    store = Store("example.sqlite")
    try:
        model = ScriptedModel((
            Response(
                calls=(Call(id="sum", name="add", arguments={"left": 17, "right": 25}),),
                finish="tool_calls",
            ),
            Response(text="The result is 42."),
        ))
        runtime = Runtime(
            model, Registry((Tool.from_callable(add),)), store,
            Policy(allowed_tools=frozenset({"add"})),
        )
        result = await runtime.run("Add 17 and 25")
        print(result.status, result.output)
    finally:
        store.close()

asyncio.run(main())
```

Swap `ScriptedModel` for a provider adapter without changing the tool admission
path. Tools and policy always remain host-owned.

## CLI and examples

```sh
agent-core --db demo.sqlite demo
python examples/offline_research.py
python examples/approved_workspace.py
python examples/uncertain_external.py
```

The research demo searches and reads prepared local evidence, computes savings
and produces a sourced result. The workspace demo requires approval and restores
the run from SQLite before writing. The external demo simulates acceptance with
a lost response and reconciles the receipt without repeating the effect.

Start an interactive approval exercise:

```sh
agent-core --db notes.sqlite --scenario workspace --workspace ./notes demo
```

Its JSON includes the run ID, operation ID, canonical arguments, expiry and
binding. Use `agent-core --help` and the
[CLI guide](docs/cli.md) to approve, resume, cancel, inspect events or reconcile.

## Architecture and guarantees

The [architecture diagram](docs/architecture.md) shows the model, admission,
execution, storage and observation boundaries. The
[execution specification](docs/specification.md) defines states and transactions.

A complete response is saved before its tools execute. A tool outcome and batch
cursor are committed together. Committed outcomes are reused after restart.
Interrupted dispatches require host reconciliation. No automatic tool retry or
arbitrary external exactly-once guarantee is provided.

## Development and verification

```sh
make check
make benchmark
make build
```

[Testing](docs/testing.md) records executed checks;
[evaluation](docs/evaluation.md) explains the oracles and overhead measurements.
The [release status](docs/release-readiness.md) distinguishes offline verification
from pending live checks. See [roadmap](docs/roadmap.md) for scope and
[progress](docs/progress.md) for continuation.

## Further documentation

- [SDK and custom tools](docs/sdk.md)
- [Permissions, approval and security](SECURITY.md)
- [Sessions and recovery](docs/recovery.md)
- [Providers and supported profiles](docs/providers.md)
- [Limits, context, events and retention](docs/limits-and-events.md)
- [Restoration and next steps](docs/continuation.md)
- [Contributing](CONTRIBUTING.md), [changelog](CHANGELOG.md)

## Current limits

Local single-agent execution, sequential tools, trusted in-process Python
functions and Linux local-file ownership. No distributed workers, MCP adapter,
GUI, browser, shell, automatic semantic memory or model token streaming. Context
limits are serialized bytes, not model-specific tokenizer guarantees. Session
membership does not imply shared conversation or inherited permissions. SQLite
contains task data in plaintext. A stopped wait cannot kill a synchronous thread.

## License

[MIT](LICENSE). Copyright Sergey Puchkov. Actual library dependencies and their
roles are documented in [dependencies](docs/dependencies.md).
