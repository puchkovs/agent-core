# Continue development

Continue the existing private main history; use `git log -1` for current commit.
Use .venv and hash-locked requirements; preserve alpha version and original history.


## Phase 12 optional MCP — 2026-11-27

Implemented an optional SDK 1.30.0 bridge for protocol 2025-11-25 tools over
Streamable HTTP. Configuration rejects non-HTTPS except explicit loopback;
connection/session cleanup uses async contexts. Discovery is atomic, paginated,
size/count bounded, schema checked and namespaced. Server annotations cannot
grant authority: every tool is EXTERNAL with an explicit permission and ordinary
Runtime validation/approval/dispatch/reconciliation. No subprocess launcher added.

Controlled local SDK servers verified both JSON and SSE HTTP responses and
in-memory approval/continuation, denial, invalid arguments and uncertain failure
without repeated effects. Limits/error cases are deterministic. Existing dependency
pins were preserved; 13 new optional SDK-related distributions are hash-locked.
`pip install --require-hashes -r requirements-dev.lock` and `pip check` pass.

Full make check: 255 passing tests, 97.41% combined coverage; MCP 96%, streaming
98%, strict mypy, Ruff lint/format and three demos pass. MCP is included in the
critical 90% component gate. Exact scope and resource-limit caveats: docs/mcp.md.
Native-streaming CI run 45930099019 passed with Node.js 24 actions.
Next: Phase 13 SDK/CLI cleanup and structured storage errors; phases 14–16 remain.

No paid-provider calls or final publication authorized. Complete phases 13–16;
rerun final package/install/advisory/documentation/CI gates after changes.
