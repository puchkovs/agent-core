# Release readiness

**Version 0.1.0a1; final v0.1.0 remains blocked.**

Current offline gate: 231 passing tests, 97.51% combined coverage; lint, formatting,
strict typing and three original demonstrations pass. The previous installed
package gate is recorded in testing.md; final builds/clean installs must be
repeated after completing the remaining implementation.

Phase 9 audit is complete for the existing sequential architecture. Phase 10
offline provider improvements are complete; live endpoint compatibility is
unverified. Native token streaming is implemented and fixture-verified for both adapters.
Runtime.stream retains lifecycle events and adds provisional model.delta records.

Remaining mandatory gates:

1. Verify native streaming against live providers after paid-call authorization.
2. Implement Phase 12 optional MCP with an explicit protocol/transport matrix.
3. Complete phases 13–15 SDK/CLI, evaluation and documentation improvements.
4. Run Phase 16 final package/install/security/documentation/CI verification.
5. Obtain paid-call authority and host credentials for opt-in live provider checks.

Private GitHub origin is synchronized at verified implementation milestones.
Phase 9 CI run 45923353317 and Phase 10 CI run 45923492372 passed. Inspect the
latest commit's CI separately. No release tag, final GitHub Release, PyPI
publication, public visibility change or paid provider call has been made.

No distributed execution, hard process sandbox or arbitrary external exactly-once
guarantee is provided. See SECURITY.md for trust boundaries and testing.md for
actual evidence and limitations.
