# Dependencies

Agent Core uses general-purpose libraries rather than an agent execution framework.

| Dependency | Role | Installed in minimal core |
|---|---|---|
| Pydantic 2 | Typed records and native callable schema generation | Yes |
| jsonschema 4 | Draft 2020-12 input/output validation | Yes |
| httpx 0.28 | Optional complete-response HTTPS model adapters | No; `providers` extra |
| Python sqlite3 / asyncio / fcntl | Local journal, scheduling and Linux ownership | Standard library |

Each installed library retains its own distribution license and notices. The
Agent Core MIT license covers original project files, not independent dependency
licenses. Wheel installation installs dependency distributions normally; their
source is not vendored here.

`requirements-dev.lock` pins the development and provider environment with
artifact hashes. `requirements-runtime.lock` pins the runtime plus optional HTTP
providers for advisory checks. Regenerate intentionally and rerun contract tests
when changing dependencies. Development tools include pytest, coverage, Ruff,
mypy, build and pip-audit. No installed library is a claim that every transitive
component has received a manual source or legal audit.

Optional MCP uses the official mcp Python SDK 1.30.0. Its HTTP/session, validation
and cryptographic dependencies retain their installed distribution notices; none
are vendored. requirements-mcp.lock records the exact optional runtime scope.
