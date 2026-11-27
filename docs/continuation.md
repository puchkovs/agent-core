# Continue from the verified offline candidate

Use the existing private puchkovs/agent-core origin/main and preserve all history.
Run `git log -1`, `git status --short` and `gh run list --limit 3` for exact current
HEAD and final CI. Source implementation completed at 52ce5db; subsequent commits
record evaluation/docs/verification. Version remains 0.1.0a1. Do not restart phases
9–15 or recreate the repository.

Independent Phase 16 gates passed: 266 tests, 97.42% combined coverage, lint/format,
strict typing, demos, builds, clean core/provider/MCP installs, installed offline
SDK/CLI smoke, dependency/advisory and history/archive/doc checks. The final CI
workflow additionally runs archive audit and installed optional SDK smoke. Verify
its conclusion before reporting final CI success. See testing.md for exact evidence.

The remaining release gate is live OpenAI and Anthropic tool/native-stream
verification. It requires explicit paid-call authority and host credentials; do
not run it merely because a key exists. Existing evaluation/live_smoke.py supports complete-response tool use and
native streaming selected by AGENT_CORE_STREAMING=1. Run each mode only after
authority is supplied. Preserve model/API/date/usage/effect evidence without keys.
Fix confirmed wire differences with deterministic fixtures; rerun make check,
builds and clean installs after any change. No final v0.1.0 claim is permitted yet.

Use existing .venv with requirements-dev.lock. MCP optional pins are also in
requirements-mcp.lock. Current package artifacts are in ignored dist/. The
reproducible audit command is `.venv/bin/python evaluation/audit_candidate.py`.
Existing benchmark/evaluation evidence is in evaluation/results; do not replace
historical results or infer model intelligence from runtime correctness fixtures.

Keep the repository private. Final release/tag, PyPI publication and paid calls
require separate authority. No further independent roadmap implementation is
currently recorded as pending for the documented compatibility scope.

Final review hardened live_smoke.py: structured sum and unpredictable tool receipt
are required. Use docs/live-verification.md for exact commands and request bounds.
No paid authority/keys are available in the reviewed session; paid tests were not
run. Audit/reverification evidence is in release-review.json; raw audit inputs stay
outside the repository. Verify the new evidence commit CI with gh run list.
