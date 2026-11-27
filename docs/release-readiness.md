# Release readiness

**0.1.0a1 verified offline candidate. Final v0.1.0 is blocked.**

Implemented phases 9–15: engineering audit, improved providers, native OpenAI and
Anthropic streaming, optional MCP SDK 1.30.0/protocol 2025-11-25 Streamable HTTP
tools, coherent SDK/CLI, expanded evaluation and current documentation.

Phase 16 independently achievable gates passed: 257 tests, 97.42% combined
coverage, critical components above 90%, lint, formatting, strict typing, three
demos, dependency consistency, pinned advisory check, builds, three clean
installation scopes, installed offline SDK/CLI smoke, history/archive/documentation
checks and preceding remote CI. Final evidence-commit CI must also pass.
See testing.md and security-reliability.md for actual scope and limitations.

## Mandatory remaining release gate

Host credentials and explicit paid-call authorization are required for live
OpenAI and Anthropic tool-use and native-stream compatibility verification. No
live compatibility claim is made. Record selected model IDs, API profiles, date,
usage and tool invocation evidence without credentials. Fix differences with
regression tests and rerun affected/full gates. Then rebuild and audit the final
candidate before considering a version change or release tag.

No other independently achievable implementation phase is currently pending for
the documented scope. Broader MCP protocols/transports, server tools, distributed
execution, process sandboxing and additional model modalities are unsupported.

Repository remains private. No paid calls, final version bump, release tag,
GitHub Release, PyPI publication or public visibility change is authorized.
