# Release readiness

**0.1.0a1 engineering candidate. Final v0.1.0 gate is not passed.**

Implemented: single-agent dynamic tools, typed contracts, schemas/semantic
checks, policies, bound approval pauses, limits/cancellation, persistent sessions,
SQLite journal/checkpoints, conservative reconciliation, context/artifact limits,
lifecycle events, usage/durations, two provider contracts, SDK, CLI, original demos,
reproducible evaluation, package builds and CI definitions.

Offline gates passed: 120 tests, 97.53% combined coverage with every critical
component above 90%, lint, formatting, strict typing, three examples, real process
crashes, source/wheel builds, two clean installs, installed offline smoke,
dependency consistency, advisory check and repository/package scans.
See [executed verification](testing.md) for exact scope and limitations.

## Remaining release work

1. Obtain explicit cost authority and host credentials for live model testing.
2. Select a real model and verify tool use against its actual provider endpoint.
   Preserve API profile, date, usage and evidence of the tool invocation.
3. Verify a real model for the second implemented contract before claiming live
   support for that adapter. Fix any differences with regression fixtures.
4. Review the intended streaming scope: this candidate implements lifecycle
   streaming and complete-response normalization, not provider token deltas.
   Native provider token streaming would require an additional tested contract.
5. Update compatibility/readiness, rerun relevant gates, build the final version
   and perform a final clean install and archive audit before tagging v0.1.0.

MCP is explicitly deferred by ADR 3 and has no compatibility claim. The current
candidate also has no distributed ownership, hard process isolation or arbitrary
external exactly-once guarantee. Advisory results are a point-in-time check, not
a comprehensive security certification.

No paid provider call, remote CI execution, release tag or remote publication
was made in this session. Do not publish from this handoff without separate
authorization. Complete history and precise continuation instructions are supplied.

## Extended release scope

The target v0.1.0 additionally requires completion of phases 9–16 in roadmap.md.
Native provider streaming and optional MCP are now required work, not accepted
release deferrals. The restored baseline has been independently reproduced and
private remote CI passed; the full new release gate remains unpassed.
