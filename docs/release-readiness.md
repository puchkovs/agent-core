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

## Audit installation verification

Implementation commit `57b7b0b60bf71f3ef0c8489bca6471b332f5a572` was pushed and
matched remote main. `git fsck --full` passed. Updated source/wheel builds passed
using hatchling 1.33.0. Clean minimal installation passed installed SDK smoke
with IP network connections blocked and no httpx installed; installed CLI demo
completed. Installing the hash-locked provider dependencies into that clean
environment also passed `pip check` and the installed offline SDK smoke with
httpx present. Distributions remain ignored under dist/ and are alpha artifacts.

Current implementation CI: run 45922819563; inspect its final conclusion using
`gh run view 45922819563`. Earlier baseline and mutation-fix CI runs passed.
These checks do not complete the extended phases 9–16 or establish native
streaming/MCP compatibility. Live verification and the full release gate remain
unpassed. Continue Phase 9 from docs/continuation.md.

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
