# Release readiness

**Version 0.1.0a1. Final v0.1.0 preparation is blocked on two Groq live checks.**

Groq complete-response and native-streaming scenarios must each verify model
selection of the arithmetic tool, one actual execution, exact sum and unpredictable
observation receipt, final structured correctness and known token usage.
Authorization covers these two scenarios exclusively within the Groq free-tier
quota, with at most six model requests combined and no automatic retry. The
execution shell reports `GROQ_API_KEY` unset; zero live requests have been sent.

| Provider | Classification | Evidence |
|---|---|---|
| Groq (`GroqModel`, OpenAI-compatible profile) | Offline-verified; live verification pending | Deterministic HTTP/SSE fixtures; live gate blocked on key availability |
| OpenAI (`OpenAIChatModel`) | Offline-verified; live verification blocked | Live attempts failed with `provider_rate_limit` (account quota); not a release gate |
| Anthropic (`AnthropicModel`) | Experimental; offline-verified | Deterministic fixtures only; not live-verified |

Successful Groq results will not establish OpenAI API compatibility. Users supply
their own credentials; no maintainer API credential is included in code or packages.

Independent offline gates remain required: complete tests/coverage, lint/format,
strict typing, demos, dependency/advisory checks, builds, clean core/provider/MCP
installs, installed smoke, documentation, history/archive audit, Git integrity,
private remote synchronization and current successful CI.

Only after both Groq scenarios and offline gates pass may v0.1.0 be prepared.
Fix confirmed live compatibility defects with deterministic regressions and rerun
affected gates before final builds. Keep selected model/API/date/usage/effect
evidence without keys. Exact procedure: [live-verification.md](live-verification.md).
No final GitHub Release, PyPI publication or public visibility change is authorized.
