# Continue development

Existing private origin/main; preserve history and alpha version.


## Phase 14 evaluation — 2026-11-27

Preserved original demos and expanded deterministic evaluation to 257 tests,
including 58 native-streaming and 24 MCP checks. Raw environment/coverage scope
is in extended-verification.json. Measured 100 samples after five warmups at
source commit 52ce5db: median 37.888701 ms, p95 48.132918 ms; raw samples,
configuration and fingerprint are in release-overhead.json. This measures
scripted runtime overhead, not intelligence or isolated transport costs.
Updated package builds passed with hatchling 1.33.0. Next: Phase 15 current-doc
reconciliation, then Phase 16 clean-install/package/security/CI checks. Live
provider verification remains blocked on paid-call authority.

Do not repeat phases 9–14. Tests: 257 passing, coverage 97.42%. Inspect latest CI
and finish current-documentation cleanup, then the final independent gates.
