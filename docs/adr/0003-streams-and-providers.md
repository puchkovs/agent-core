# ADR 3: Complete model envelopes and durable lifecycle cursors

Accepted, 2026-11-27; original candidate deferrals superseded below.

Use two different HTTP message contracts to exercise provider-neutral execution.
Accept complete responses only. Preserve required opaque replay blocks and reject
unsupported kinds rather than flattening them into text. Expose capability flags
without claiming universal model support.

Stream committed lifecycle events by cursor. This avoids turning UI consumption
into an execution-state owner and bounds memory for slow readers. Token streaming
is deferred. A broken or truncated HTTP response cannot dispatch a partial call.

MCP is deferred from this candidate. No versioned released-SDK/transport fixture
matrix has been established, and adding a new execution path before that gate
would weaken the declared compatibility boundary. It remains an optional later
adapter over the existing registry, validation, policy and journal.

## Extension: native streaming and MCP

The complete-envelope authority boundary remains unchanged. Phase 11 added native
provider streaming with provisional observations and terminal response assembly;
only the complete envelope enters admission. Phase 12 added an optional MCP SDK
bridge into existing Tool registration and policy, with no process launcher.
The former deferrals above describe the historical candidate. Current compatibility
and evidence are specified in streaming.md, mcp.md and testing.md.
