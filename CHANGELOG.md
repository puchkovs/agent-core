# Changelog

## 0.1.0 — 2026-11-27

First release preparation (private; not tagged or published). Highlights:
see [release notes](docs/release-notes-0.1.0.md).

- Add `GroqModel`, an OpenAI-compatible profile for Groq with native streaming,
  `x_groq` usage normalization, reasoning controls for documented models and a
  final-JSON fallback in place of schema output that Groq does not offer with tools.
- Live-verify Groq `openai/gpt-oss-20b` in complete-response and native-streaming
  modes (four requests, free tier); evidence in
  `evaluation/results/groq-live-verification.json`.
- OpenAI remains offline-verified (live blocked by account quota); Anthropic remains
  experimental and offline-verified.
- Include optional MCP Streamable HTTP tools, native streaming for OpenAI-compatible
  and Anthropic adapters, SDK, CLI and offline demonstrations from the alpha line.
- Add a version-consistency test and derive archive-audit file names from the
  project version.

## 0.1.0a1 — 2026-11-27

Initial engineering candidate: sequential model-directed tools; strict argument
contracts; host-owned policy; expiring, bound approvals; SQLite sessions,
checkpoints and operation journal; explicit reconciliation; bounded context and
outputs; lifecycle event cursors; usage accounting; optional OpenAI Chat and
Anthropic Messages adapters; Python SDK, CLI and three offline demonstrations.

Native OpenAI/Anthropic streaming and optional MCP tools were subsequently
implemented and offline-verified. (Historical note: this alpha was superseded by
0.1.0.)
