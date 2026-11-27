# Agent Core 0.1.0 release notes

Agent Core is a local Python runtime for model-directed, multi-step tool use. The
host owns tools, permissions, approvals and budgets; SQLite records admission and
outcomes so interrupted work is never blindly replayed. Distribution:
`agent-core-runtime`; import namespace: `agent_core`; license: MIT; CPython 3.12 on
Linux. This release is prepared in a private repository and is not published.

## What is included
- Sequential model-directed tool loop with JSON Schema and semantic validation,
  strict callable checks, deny-by-default policy and exact approval binding.
- Durable sessions, journal, checkpoints, cancellation, deadlines and explicit
  reconciliation of uncertain external effects; no automatic replay.
- Context management, execution budgets, lifecycle events and usage accounting
  (unknown usage stays unknown).
- Adapters: Groq and OpenAI Chat Completions (OpenAI-compatible wire format) and
  Anthropic Messages (experimental), each with native token streaming assembled and
  validated before any tool is dispatched.
- Optional MCP Streamable HTTP tools through host policy; Python SDK; CLI; three
  offline demonstrations; deterministic evaluation and overhead benchmark.

## Provider verification
| Provider | Status |
|---|---|
| Groq | Live-verified for `openai/gpt-oss-20b`: complete-response and native streaming, 2026-11-27, four requests |
| OpenAI | Offline-verified; live verification blocked by API rate limit/quota |
| Anthropic | Experimental; offline-verified |

The live scenario had the model choose an arithmetic tool, the host execute it
once, and the final JSON reproduce the sum and an unpredictable tool receipt, with
known usage ([evidence](../evaluation/results/groq-live-verification.json)).
It is a smoke result for one model: it does not establish other models, native
structured-output guarantees, broad quality or OpenAI API compatibility.

## Known limits
Native Python tools run with process privileges; there is no operating-system
sandbox, multi-tenant server, distributed fencing or automatic retention. Groq
returns no JSON-schema guarantee together with tools or streaming, so the final
answer is host-validated. Rate limits and model availability change; see
[providers.md](providers.md). Users supply their own API credentials.

## Verification summary
296 tests, 97.52% combined branch-aware coverage, strict typing, lint/format, offline
demos, clean core/provider/MCP installs, dependency advisory checks and
archive/history audit passed; see [testing.md](testing.md).
