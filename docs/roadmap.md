# Implementation roadmap

| Phase | Depends on | Work and acceptance gate |
|---|---|---|
| 0 | Input review | Specify states, authority, uncertainty, transactions; review contradictions |
| 1 | 0 | Contracts, registry, scripted model, bounded loop; offline safety tests |
| 2 | 1 | Exact approval binding, expiry, restart and changed-scope tests |
| 3 | 2 | WAL store, checkpoints, locks, crash injection and reconciliation |
| 4 | 3 | Two distinct provider contracts; wire fixtures; opt-in live smoke |
| 5 | 3–4 | Bounded projection/artifacts, event cursors, SDK and CLI |
| 6 | 5 | MCP only after versioned local conformance; otherwise explicitly defer |
| 7 | 1–5 | Three original demos, adversarial tests and raw overhead measurements |
| 8 | 7 | Ruff, typing, coverage, build, clean install, dependency/cleanliness audit |

Phase 0 review: accepted. No automatic tool retries; uncertain operations require
host reconciliation; byte limits are not represented as tokenizer guarantees;
thread cancellation cannot terminate arbitrary native code; live and mocked
provider verification must be reported separately. These choices resolve the
critical contract conflicts before implementation.

## Extended release roadmap

The following supersedes the earlier candidate deferrals for the target release.

| Phase | Status | Acceptance |
|---|---|---|
| 9 Engineering audit | Complete for current architecture | Review all boundaries; regression fixes and full checks |
| 10 Providers | Offline complete; live gate blocked | Official contract review, deterministic fixtures, opt-in live matrix |
| 11 Native streaming | Next | Bounded deltas and complete validated assembly; interruption tests |
| 12 Optional MCP | Pending | Versioned protocol/transport scope; local server conformance through Tool Engine |
| 13 SDK/CLI | Pending | Complete continuation, cleanup and structured-error flows |
| 14 Evaluation | Pending | Expanded scenarios and raw reproducible overhead evidence |
| 15 Documentation | Pending | Verify supported commands and compatibility scope |
| 16 Final gates | Pending | All local/CI/package/security gates; explicit release blockers |
