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
