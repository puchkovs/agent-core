# Changelog

## Unreleased

- Add `GroqModel`, an OpenAI-compatible profile for Groq with native streaming,
  `x_groq` usage normalization, documented reasoning controls and a final-JSON
  fallback in place of unsupported tool-compatible schema output.
- Live gate for v0.1.0 changed from OpenAI to Groq (free tier); OpenAI is
  offline-verified with live verification blocked by quota; Anthropic remains
  experimental. No live Groq result is recorded yet.

## 0.1.0a1 — 2026-11-27

Initial engineering candidate: sequential model-directed tools; strict argument
contracts; host-owned policy; expiring, bound approvals; SQLite sessions,
checkpoints and operation journal; explicit reconciliation; bounded context and
outputs; lifecycle event cursors; usage accounting; optional OpenAI Chat and
Anthropic Messages adapters; Python SDK, CLI and three offline demonstrations.

Native OpenAI/Anthropic streaming and optional MCP tools were subsequently
implemented and offline-verified. OpenAI live verification remains a final-release
gate. Anthropic is experimental and offline-verified, not live-verified. This
candidate is not the final v0.1.0 release and is not published to a package index.
