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
