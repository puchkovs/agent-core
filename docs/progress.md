# Progress

Current extended candidate: 266 passing tests, 97.42% combined coverage. Native
streaming and optional MCP are implemented for their documented offline scopes.
The sections below retain historical verification milestones; they are not all
statements about the current implementation. Live-provider verification is pending.

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

## Phase 15 documentation — 2026-11-27

Reconciled README, specification, architecture, security, providers and limits
with current native streaming and MCP scope. Preserved historical ADR/evaluation
evidence with explicit supersession notices. Local Markdown file links resolve;
all Python doc blocks parse; README quick start executed successfully (result 42).
CLI --help runs. Existing documented offline demos and lifecycle commands remain
covered by the passing 257-test suite. Live/placeholder endpoint examples are
configuration illustrations, not claimed executed service verification.
Next: Phase 16 final gates, clean installations and candidate archive audits.

## Phase 16 independent final gates — 2026-11-27

Final make check passed: 257 tests, 97.42% combined coverage, every critical
component above 90%, Ruff lint/format (39 Python files), strict mypy (18 source
files) and three demos. Dependency consistency and git fsck --full passed.
Updated alpha source/wheel builds passed with hatchling 1.33.0.

Clean minimal, provider and MCP installations passed the installed offline SDK
smoke; minimal core contains neither httpx nor mcp. Installed CLI demo passed.
Provider/MCP clean pip check passed. Pinned optional MCP advisory scan returned
no known vulnerabilities. Raw environment/coverage, advisories and benchmarks are
under evaluation/results. Current archive/history audit passed across 190 blobs,
including original ancestry, credential patterns, wheel/source comparison, archive
paths, license/typing markers and local documentation. Counts grow with evidence
commits; rerun evaluation/audit_candidate.py for current counts.

All preceding milestone CI runs passed, including documentation run 45930938229.
Final CI adds full-history checkout, reproducible archive audit and clean installed
SDK/MCP smoke; inspect its conclusion after pushing this final evidence commit.
Security/reliability report: docs/security-reliability.md.

Remaining mandatory blocker: real OpenAI and Anthropic endpoint/tool/native-stream
verification requires host credentials and explicit paid-call authorization.
No paid call, final version bump, release tag, GitHub Release, PyPI publication or
public visibility change occurred. All independently achievable phases 11–16
are completed for the documented scope; Phase 16 release gate remains blocked.

Live verification preparation: live_smoke.py now supports AGENT_CORE_STREAMING=1,
records API profile/date/mode and requires known usage. Its disabled guard was
verified locally; no paid endpoint was contacted.

## Final release review — 2026-11-27

Verified restored review HEAD f21cde0da23a42d97559ce82c1eb791fc89a396d matched private
origin/main and CI run 45931321486 passed. Reviewed all 18 reachable commits,
203 historical blobs, commit subjects, refs (no tags), working tracked/untracked
files and hidden-file inventories. Only legitimate Agent Core/dependency materials
were identified. No inappropriate historical content requiring correction was
found; no history was rewritten. Raw audit inputs remain outside the repository.
Credential-pattern and reference scans are scoped evidence, not a universal proof.

Strengthened live smoke to require structured sum 42 plus an unpredictable receipt
returned only by actual tool execution. Nine offline procedure regressions verify
both provider/mode combinations, reject fabricated receipts and enforce opt-in.
The live procedure is bounded to three turns, one tool, 60 seconds and 128 output
tokens per turn. docs/live-verification.md gives all four exact Bash commands,
silent key setup, model requirements, expected usage and final release checklist.
Its shell syntax was checked without executing the paid commands. Neither provider
key is present in this process environment; no paid requests were made.

Actual final make check: 266 tests pass, 97.42% combined coverage, every critical
component above 90%, Ruff lint/format (40 files), strict mypy (18 source files) and
all three demos. Builds, archive/source/link audit, three clean installation scopes,
installed SDK/CLI smoke, dependency consistency and git fsck pass. Fresh pinned
MCP/runtime advisory scan returned no known vulnerabilities. Raw verification and
advisories: evaluation/results/release-review*.json. Version remains 0.1.0a1.

Remaining: explicit paid-call authorization, authorized provider keys/model IDs,
four successful live checks, fix any wire differences with regressions, then refresh
relevant gates and final package/CI evidence before considering final versioning.
Publication/visibility changes require separate authorization.

## OpenAI-only release acceptance — 2026-11-27

Revised acceptance per host direction: OpenAI non-streaming and native-streaming
live tool/receipt verification are mandatory; Anthropic is experimental and
offline-verified, not live-verified. Anthropic implementation/tests are preserved.
Every user supplies their own credentials; none is embedded in distributions.
Paid authorization covers these two OpenAI scenarios only, six model requests
combined, with no automatic retry. Zero paid requests have been sent.

Credential presence checks in login and non-login execution shells both report
OPENAI_API_KEY unset. Requested secure session-environment availability without
asking for the key in chat. This is credential access, not missing cost authority.
No live model/usage/result evidence exists yet; v0.1.0 preparation remains blocked.
Model selection must confirm account availability before consuming generation
requests; no current model is claimed live-compatible.

Offline gates passed: 266 tests, 97.42% combined coverage, strict mypy, Ruff
lint/format, three demos, builds, clean core/provider/MCP installs, installed
SDK/CLI smoke, pip check, documentation checks and git fsck. Fresh pinned advisory
scan returned no known vulnerabilities. Audited 212 reachable blobs and working
files; no inappropriate reference/credential-pattern findings. Installation logs
and distribution members also passed credential-pattern scans. Raw audit inputs
remain outside the repository. Without the actual key in this process, exact
literal-key comparison cannot be performed; pattern checks are scoped evidence.
No history was rewritten, no credentials printed, no paid requests/retries made.

## Groq profile and live-gate handover — 2026-11-27

Started at 75f7453 (remote CI green). Added `GroqModel` (see providers.md): shared
envelope/SSE validation, `x_groq` usage normalization, reasoning controls only for
documented models, final-JSON fallback for the missing tool-compatible schema
output, and a repeated-usage rule that is Groq-only (OpenAI still rejects any
duplicate receipt). The opt-in live script gained a Groq mode requiring
`AGENT_CORE_GROQ_FREE_TIER=1`, a 512-token output budget for hidden reasoning and
an `output_token_limit` evidence field. Committed as 14f265f.

Offline gates on the final tree: `make check` passed with 295 tests and 97.43%
combined coverage (critical-component gate passed, groq.py fully covered), strict
mypy, Ruff lint/format, three demos. Source/wheel builds, clean core and MCP
installations with installed SDK/CLI smoke and `pip check`, and Groq import from
the installed wheel passed. pip-audit on the runtime and MCP locks reported no known
vulnerabilities. `evaluation/audit_candidate.py` passed over 231 historical blobs
plus archives and docs; separate pattern scans of tracked files, commit messages,
branches (main only) and tags (none) found no credential patterns or inappropriate
references. The key variables were unset, so no literal-key comparison was possible.
Benchmarks were not rerun; no hot path changed beyond one conditional.

**Live verification: not run.** `GROQ_API_KEY` is not available to the execution
environment, so zero Groq requests were sent. Version stays 0.1.0a1. Next: run the
two commands in live-verification.md from a local terminal, then follow
continuation.md. Nothing has been pushed; origin/main remains 75f7453.
