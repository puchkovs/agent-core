# Continue development

Continue private origin/main with existing .venv; preserve alpha version/history.


## Phase 13 SDK and CLI — 2026-11-27

Added Store context-manager cleanup on normal exit and host exceptions. CLI now
returns structured storage_error for database initialization/I/O failures and
unknown_run for events on absent runs; raw storage details are not emitted.
Existing continuation, approval, cancellation, reconciliation, schema, typing and
cleanup flows remain verified, including native streaming and optional MCP.

Full make check passed: 257 tests, 97.42% combined coverage, all critical modules
above 90%, strict mypy, Ruff lint/format and three demos. Optional MCP pinned
advisory scan returned no known vulnerabilities; raw mcp-advisories.json retained.
Next: Phase 14 record updated benchmark/evaluation evidence, then documentation
and final verification. Live endpoint verification remains blocked by cost authority.

Phases 11–13 are implemented offline; live-provider gates remain. Complete phases
14–16 and inspect CI for each pushed milestone. No paid calls or release publication.
