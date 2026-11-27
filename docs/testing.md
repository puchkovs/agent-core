# Executed verification

2026-11-27; CPython 3.12.14; Linux x86_64; SQLite WAL, synchronous FULL.
Exact tool versions and raw summaries are in
[offline-verification.json](../evaluation/results/offline-verification.json).

| Gate | Actual result |
|---|---|
| Ruff lint and format | Passed, 35 Python files formatted |
| Strict mypy | Passed, 15 source modules |
| Offline pytest suite | 120 passed; no skipped live tests disguised as coverage |
| Combined statement/branch coverage | 97.53% |
| Statement coverage | 98.20% (1089/1109) |
| Branch coverage | 95.40% (332/348) |
| Critical runtime coverage | Runtime 96.37%; contracts, store, tools, policy and context 100% |
| Original examples | Three passed |
| Real process-death/restart checks | Passed at model-start, model-envelope, dispatch and outcome boundaries |
| Source and wheel builds | Passed; build backend hatchling 1.33.0 |
| Clean minimal-core installation | Passed; optional HTTP dependency absent |
| Clean provider-extra installation | Passed |
| Installed-package offline smoke | Passed in both clean environments with IPv4/IPv6 connections blocked |
| Installed CLI | Research demo completed from the installed wheel |
| Dependency consistency | Passed for the clean provider environment |
| Advisory check | 16 pinned runtime/provider dependencies; no known advisories returned |
| Local Markdown links | All resolved |
| Text/reference/package audit | Passed; complete reachable blobs and distribution members scanned |
| Live model endpoint | Not run; requires explicit cost authority and host credentials |
| Remote CI | Workflow prepared; not run remotely |
| GitHub/PyPI publication | Not performed |

Commands executed:

```sh
make check
make build
python evaluation/benchmark.py --output evaluation/results/overhead.json
pip-audit -r requirements-runtime.lock --no-deps --disable-pip --format json
python evaluation/installed_smoke.py
```

The installed smoke was invoked using each clean environment's interpreter.
It asserts import from site-packages and prevents IP network connections. Package
members were compared byte-for-byte with current Python source. The hash-locked
requirements define the advisory scan's exact scope. No comprehensive transitive
manual security review or external penetration test is claimed.

The suite covers unit, integration, provider-contract, CLI/E2E, security,
architecture and real crash behavior. Its high coverage does not replace the
listed behavioral oracles, nor prove model intelligence or production security.
Raw provider fixture failures are intentionally deterministic; no paid endpoint
is contacted by normal tests.

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
