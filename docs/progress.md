# Progress

| Phase | Actual state |
|---|---|
| 0 | Complete: original specification, architecture, ADRs and roadmap |
| 1 | Complete: typed foundation, registry, scripted model, bounded sequential loop |
| 2 | Complete: deny-by-default policy, semantic checks, expiring bound approvals |
| 3 | Complete: SQLite sessions/journal, response/outcome checkpoints, file ownership, reconciliation |
| 4 | Implemented and fixture-verified for two contracts; live endpoint gate pending |
| 5 | Complete candidate scope: context/artifacts, lifecycle cursors, usage/durations, SDK and CLI |
| 6 | Deliberately deferred: no MCP compatibility claim |
| 7 | Complete offline evaluation: three original demos, 120 tests and 100 raw overhead samples |
| 8 | Offline gates complete; final release blocked by live provider gate |

Latest offline gate: 120 tests pass, 97.53% combined statement/branch coverage;
critical modules independently exceed 90%. Ruff, strict mypy and three examples
pass. Real subprocess crashes have been verified at dispatch, outcome and model
response boundaries, including loss of the usage receipt. No real provider call, remote CI run or publication occurred.

Build/install/advisory and package audit passed. Handoff includes the full local
history, bundle and candidate distributions. Next: follow continuation.md for
explicitly authorized live compatibility checks; do not restart completed work.

## Restored repository audit — 2026-11-27

Verified original HEAD `c931cf976fa51e4eb664f529e818c40df2c872d0` and all five
reachable commits; `git fsck --full` passed. Author identity is configured locally.
Reviewed tracked paths, commit metadata, historical blob types, distribution
members and credential/unrelated-material patterns across 87 reachable blobs.
No pattern findings; this is not a guarantee that every possible secret is detectable.
Created private `puchkovs/agent-core`; original remote main matched HEAD exactly.
Baseline GitHub Actions run 45922505014 passed.

Independently reproduced baseline from a temporary export of the exact commit:
CPython 3.12.3, 120 tests, 97.53% combined coverage, Ruff, strict mypy and all
three offline demos passed. Hash-locked development installation succeeded.

Phase 9 is in progress. Fixed mutation of semantic-validator arguments by using
an isolated JSON copy and rejecting changed arguments before dispatch. Rejected
NaN/infinite tool timeouts at registration. Five added regression cases pass:
125 tests, 97.54% combined coverage; every critical module exceeds 90%.
`make check` and dependency consistency passed. No dependency versions changed.

Remaining work: finish the engineering audit, then phases 10–16, including native
provider streaming and optional MCP. Live provider calls still require explicit
cost authority. No release tag, PyPI publication or public visibility change.

## Strict callable admission follow-up

Generated callable arguments now undergo strict Pydantic validation before
approval or dispatch for both synchronous and asynchronous functions. Regression
cases use integral floating-point input accepted by JSON Schema but rejected by
strict Python integer validation; neither write executor runs, and both produce
`invalid_arguments` rather than an uncertain dispatched write.

Full `make check PYTHON=.venv/bin/python`: 127 tests pass, 97.56% combined
coverage, all critical modules above 90%, Ruff/format, strict mypy, three demos.
Dependency consistency passed; fresh runtime/provider advisory scan returned no
known vulnerabilities (raw `evaluation/results/audit-advisories.json`).
First audit commit `61b8864` passed remote CI run 45922709736.

Raw overhead results from the earlier mutation/timeout working tree are retained
in `evaluation/results/audit-overhead.json`: 100 measured samples after five
warmups, median 84.9472275 ms, p95 122.097046 ms. The file records its dirty
source fingerprint and base commit; it does not measure the later strict-input
change. Host/filesystem conditions differ from the historical 2 ms run; no
regression attribution or model-intelligence claim follows from this comparison.

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

## Phase 11 native streaming — 2026-11-27

Implemented bounded HTTP SSE streaming, OpenAI and Anthropic assembly, typed public
ModelDelta SDK events, opt-in streaming=True complete(), and Runtime integration
inside model-inflight/complete-response checkpoints. Durable lifecycle cursors
remain intact; model.delta is provisional. Complete validated terminal envelopes
alone authorize admission. Tested fragmented/multiple calls, usage, thinking
replay, malformed transitions, missing terminals, disconnects, timeouts,
cancellation, cleanup, bounds, backpressure and split-secret journal suppression.

Full make check passed: 231 tests, 97.51% combined coverage; assembly 98%, strict
mypy, Ruff lint/format and all three demos pass. Added stream/transport components
to the per-component 90% coverage gate. CI action metadata confirms Node.js 24 for
checkout v5/setup-python v6; updated workflow keeps all existing verification.
Live-provider verification remains blocked by absent paid-call authority.
Next: Phase 12 optional MCP protocol/transport implementation and local conformance.

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
