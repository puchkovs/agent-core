# Release readiness

**Version 0.1.0. Release preparation is complete; publication has not been
authorized or performed.** No tag, GitHub Release or package-index upload exists.

The mandatory Groq gate passed on 2026-11-27: for `openai/gpt-oss-20b`, both the
complete-response and native-streaming scenarios showed model selection of the
arithmetic tool, one actual host execution, the exact sum and an unpredictable
tool receipt in the final structured answer, and known token usage. Four model
requests were made within the free-tier allowance (ceiling six), with no automatic
retry. Sanitized records: [groq-live-verification.json](../evaluation/results/groq-live-verification.json).

| Provider | Classification | Evidence |
|---|---|---|
| Groq (`GroqModel`) | Live-verified for `openai/gpt-oss-20b` | Two live scenarios (4 requests) plus deterministic HTTP/SSE fixtures |
| OpenAI (`OpenAIChatModel`) | Offline-verified; live verification blocked | Live attempts failed with `provider_rate_limit` (account quota); not a release gate |
| Anthropic (`AnthropicModel`) | Experimental; offline-verified | Deterministic fixtures only; not live-verified |

Successful Groq results do not establish OpenAI API compatibility, other Groq
models, native structured-output guarantees or broad task quality. Users supply
their own credentials; no maintainer API credential is included in code or packages.

Offline gates for this release are recorded in [testing.md](testing.md): tests and
coverage, lint/format, strict typing, demos, dependency advisories, builds, clean
core/provider/MCP installs, archive/history audit, Git integrity and CI.

Remaining actions need separate authorization: create the `v0.1.0` tag, publish a
GitHub Release, publish to a package index, or change repository visibility
(currently private). Release notes: [release-notes-0.1.0.md](release-notes-0.1.0.md).
