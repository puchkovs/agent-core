# Continue development

Continue private origin/main; `git log -1` gives the current framing milestone.
Preserve all five original commits and subsequent history. Use existing .venv
and `make check PYTHON=.venv/bin/python`; no new dependency versions are needed.
Do not repeat baseline reproduction or completed Phase 9/10 offline work.


## Phase 11 framing foundation — 2026-11-27

Added original incremental SSE framing with a total wire-byte limit, strict UTF-8,
BOM support, LF/CRLF/CR line endings, multiline data, comment/unknown-field
handling, pull backpressure and cancellation propagation. Unterminated frames
fail closed. No reconnect or replay is implemented. This is an internal framing
foundation: provider native streaming is not yet connected or advertised.

Full make check passed: 173 tests, 97.70% combined coverage, all critical modules
above 90%, Ruff lint/format, strict mypy (16 source files), and three offline demos.
Provider milestone commit `616e4ee` passed CI run 45923492372. Phase 9 commit
`40b8dbf` passed CI run 45923353317.

Next: implement bounded HTTP SSE consumption and provider-specific stream
assemblers, then expose text/argument/usage deltas and complete validated response
assembly. Require provider terminal events, test multiple calls, malformed events,
interruptions, timeouts and no partial dispatch. Phase 11 is incomplete; phases
12–16 remain outstanding. Live calls still require paid-call authority.

See docs/providers.md for the reviewed provider profile and usage semantics.
The SSE parser is src/agent_core/providers/sse.py, with tests/test_streaming.py.
Existing Runtime.stream remains durable lifecycle events only. New deltas must
never grant execution authority. Keep final v0.1.0 and public publication blocked
until all mandatory gates pass. No paid API call is authorized.
