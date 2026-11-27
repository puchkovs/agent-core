# Agent Core

Agent Core is a local Python runtime for model-directed, multi-step tool use.
The host controls tools, permissions, approvals and budgets. SQLite records
operation admission and outcomes so interrupted writes are not blindly repeated.

Current version: **0.1.0a1**, an engineering candidate. Live-provider verification
is required before a v0.1.0 release. Native Python tools run with process privileges.

## Install

Requires Python 3.12+ on Linux. From this checkout:

```sh
python -m venv .venv
. .venv/bin/activate
pip install -e '.[dev,providers]'
```

See [execution contracts](docs/specification.md), [architecture](docs/architecture.md),
[roadmap](docs/roadmap.md) and [verification](docs/testing.md).

## License

MIT. Copyright Sergey Puchkov.
