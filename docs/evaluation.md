# Evaluation and benchmarks

The deterministic suite measures runtime correctness separately from model
intelligence. The model fixture can branch on actual observations; the runtime
has no domain-specific dispatch sequence. Fixtures are original and local.

| Scenario | Success oracle |
|---|---|
| Local evidence synthesis | Search/read tools return prepared files; savings are 6 kWh/day and 24 synthetic credits/month, with three source IDs and a limitation |
| Approved workspace write | No write before approval; approval survives a new store/runtime; one note matches exact bytes |
| Lost external response | One service receipt; uncertain state survives resume; reconciliation produces final output without another receipt |
| Crash before dispatch commit | No effect until a successful admission commit |
| Process death after dispatch commit | Uncertain state on restart, even if effect had not started |
| Crash after outcome commit | Saved cursor/result reused; no duplicate tool |
| Process death after model envelope commit | Saved response reused; proposal/final is not lost |
| Changed authority or expired approval | No tool execution |
| Truncated provider response | No partial tool execution |

Security regressions count actual forbidden executions, not just refusal text.
Additional tests cover structural/semantic input rejection, output validation,
stream closure, slow event consumers, context turn integrity, event ordering,
thread timeout uncertainty, token accounting and configuration drift.

Run `make check` for the full offline gates. Unit, integration, provider-contract,
CLI/E2E, process-crash, security and architecture checks are combined in pytest.
No dataset score, real-model task success rate or benchmark-superiority result
is claimed. Live-provider smoke is a separate opt-in gate.

## Overhead protocol

`make benchmark` runs 5 warmups and 100 measured samples. Each sample creates a
new SQLite WAL/FULL database, drives two scripted model responses and one integer
addition tool, checks the actual result, and counts committed events. The raw JSON
records interpreter, platform, SQLite/dependency versions, source hash, commit,
configuration and all sample durations. Median and nearest-rank p95 are descriptive
statistics on this shared container, not latency guarantees.

The elapsed measurement includes database creation and filesystem synchronization.
It excludes network/model latency and measures no LLM intelligence. Thread startup,
cache, filesystem and shared scheduling affect the numbers. Reproduce the command
and compare configurations explicitly before drawing performance conclusions.

Measured candidate: median 2.0021885 ms, nearest-rank p95 2.312309 ms across
100 samples. See [raw results](../evaluation/results/overhead.json) and
[final verification](final-verification.md) for source provenance and caveats.

## Extended candidate evaluation

The expanded deterministic suite includes 58 native-streaming tests and 24 MCP
checks plus 175 contracts/runtime/recovery/CLI/framing checks: 257 total.
Streaming oracles require terminal validation before dispatch and unknown usage
after interruption. MCP checks count actual server effects: no write before
approval, no invalid/denied invocation and no replay after uncertain failure.
JSON and SSE HTTP responses are tested against a controlled loopback SDK server.

[Extended verification](../evaluation/results/extended-verification.json) records
actual environment and coverage. [Current overhead](../evaluation/results/release-overhead.json)
records 100 samples after five warmups at source commit 52ce5db: median
37.888701 ms, p95 48.132918 ms. This measures ordinary single-tool runtime
overhead, not isolated MCP/streaming costs. Host/filesystem differences prevent
attributing changes against historical runs. No model intelligence score is claimed.
