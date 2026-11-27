# Release readiness

**Version 0.1.0 is published** as a [GitHub Release](https://github.com/puchkovs/agent-core/releases/tag/v0.1.0) (tag `v0.1.0`,
commit `e639cb54c19b07363652960cb38a88fe493ace5d`, 2026-11-27). The repository is
public. The package is not published to PyPI. Maturity: alpha.

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

Release gates (recorded in [testing.md](testing.md)): 296 tests, 97.52% combined
coverage, lint/format, strict typing, demos, dependency advisories, builds, clean
core/provider/MCP installs, archive/history audit, Git integrity and CI.

Published assets and SHA-256 checksums:

```
811d2d8bab0f308146327639f1d6fe4d7872bec46124715edba81bcaf9a28ef8  agent_core_runtime-0.1.0-py3-none-any.whl
149cd8b5f903ca73a3f91327c6cf9f21c0a00f2482d1d62b20b842b5193e092d  agent_core_runtime-0.1.0.tar.gz
```

Not done: PyPI or other package-index publication. Release notes:
[release-notes-0.1.0.md](release-notes-0.1.0.md).
