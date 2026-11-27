# Release readiness

Version: 0.1.0a1 engineering candidate, not final v0.1.0.

The offline runtime, approvals, persistence, two provider contracts, SDK, CLI and
three demonstrations are implemented. Required offline checks are being completed
and recorded in testing.md. MCP is explicitly deferred by ADR 3.

## Remaining mandatory gate

At least one real provider endpoint must pass an explicitly authorized live
smoke with a declared model and API profile. Neither HTTP fixtures nor documentation
inspection establish that gate. No paid calls are authorized by the current task.
The second provider also needs a concrete supported-model compatibility record
before broader interoperability claims.

Do not tag v0.1.0, publish to GitHub or upload to a package index from this session.
CI workflow files are prepared; remote CI has not run. Local candidate builds
are useful for review and continuation, not a claim of final release acceptance.
