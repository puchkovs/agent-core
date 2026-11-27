# Release readiness

**Version 0.1.0a1. Final v0.1.0 preparation is blocked on two OpenAI live checks.**

OpenAI complete-response and native-streaming scenarios must each verify model
selection of the arithmetic tool, one actual execution, exact sum and unpredictable
observation receipt, final structured correctness and known token usage.
Paid authorization exists for these two scenarios exclusively, with at most six
model requests combined and no automatic retry. The execution shells currently
report OPENAI_API_KEY unset; zero paid requests have been sent in this continuation.

Anthropic is experimental and offline-verified, not live-verified. Its adapter and
deterministic tests remain supported experimentally; Anthropic live checks are
not mandatory release gates. Users supply their own credentials. No maintainer
API credential is included in code or packages.

Independent offline gates remain required: complete tests/coverage, lint/format,
strict typing, demos, dependency/advisory checks, builds, clean core/provider/MCP
installs, installed smoke, documentation, history/archive audit, Git integrity,
private remote synchronization and current successful CI.

Only after both OpenAI scenarios and offline gates pass may v0.1.0 be prepared.
Fix confirmed live compatibility defects with deterministic regressions and rerun
affected gates before final builds. Keep selected model/API/date/usage/effect
evidence without keys. Exact procedure: [live-verification.md](live-verification.md).
No final GitHub Release, PyPI publication or public visibility change is authorized.
