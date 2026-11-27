# Continue development

Private origin/main preserves all original history. Read `git log -1` for current
commit. Use existing .venv; do not repeat baseline reproduction.


## Phase 10 provider improvements — 2026-11-27

Completed the offline provider review and fixes: strict token counters, Anthropic
cache-aware input accounting, selected provider identity/raw usage metadata,
malformed-object classification, refusal validation and rejection of falsy
nontext OpenAI content. Existing replay/tool-call/structured-output fixtures
remain passing. Endpoint/model identifiers remain host-configurable.
Official reference links and exact profile limitations are in docs/providers.md.

Full make check: 158 tests pass, 97.64% combined coverage, all critical components
above 90%, Ruff/format, strict mypy and three demos. Phase 9 CI run 45923353317
passed. No dependency versions changed or paid endpoint calls occurred.
Phase 10 offline work is complete; live interoperability remains a release blocker
because paid-call authority is absent. Next independently achievable task is
Phase 11 native provider streaming with bounded parsing and complete assembly.

Next: implement Phase 11. Preserve the existing lifecycle event stream. Provider
deltas must not authorize tool execution; only complete validated responses can
be checkpointed for dispatch. Cover fragments, multiple calls, missing terminal
events, cancellation, timeouts, backpressure and malformed events. Then phases
12–16 remain. Keep version alpha, origin private and no final publication.
