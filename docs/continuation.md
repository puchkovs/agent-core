# Continue development

Current working history is on private origin/main; use `git log -1` for the
latest commit. Preserve all history and remain on the alpha version.


## Phase 9 admission and transport audit — 2026-11-27

Reviewed the existing sequential state machine, tool admission, host policy,
SQLite dispatch/outcome boundaries, conservative recovery, context groups,
cancellation, budgets, local ownership, SDK/CLI and packaging. Existing crash,
authority and recovery regressions remain passing. The review does not establish
hard process isolation, distributed fencing or arbitrary external exactly-once effects.

Closed transaction-time deadline/approval races and model-admission cancellation:
checks now occur after acquiring the SQLite write transaction. Failed admission
rolls back without dispatch, tool-count increments or loss of known model usage.
Transport rejects duplicate JSON object keys and nonfinite timeouts, prevents
redirect following even on caller-owned clients, and checks chunk size before
extending the response buffer. No automatic retries were added.

`make check PYTHON=.venv/bin/python` passed: 135 tests, 97.72% combined coverage,
all critical components above 90%, Ruff lint/format, strict mypy and three demos.
Phase 9 review is complete for the current architecture; new provider, streaming
and MCP behavior will require their own verification. Next: Phase 10 provider
shape validation, usage accounting and metadata against official references.
Live calls remain blocked on explicit paid-call authority.

Use the existing .venv and hash-locked dependencies. Do not repeat the restored
repository audit or baseline reproduction. Next phases remain 10–16 in roadmap.md.
