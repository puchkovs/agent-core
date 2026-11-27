# Optional MCP tools

Install `pip install '.[mcp]'`. The verified SDK pin is `mcp==1.30.0` and the
negotiated protocol scope is **2025-11-25**. Agent Core's bridge is original code
over that dependency; SDK distributions retain their own licenses. Core imports
do not import MCP. Development locks include the SDK for deterministic tests;
requirements-mcp.lock pins the runtime plus MCP environment with artifact hashes.

Supported scope: tools/list, pagination, tools/call, typed structured results and
Streamable HTTP through the SDK. Controlled loopback tests cover stateless JSON
and SSE responses, initialization, discovery, execution and cleanup. In-memory
SDK servers additionally verify approvals, denials, invalid arguments and no
replay after uncertain failure. This is not universal MCP-server certification.
Other protocol revisions, stdio/process launch, resources, prompts, roots,
sampling, elicitation, task-augmented calls and automatic discovery refresh are
outside the supported API. Server-provided instructions are not adopted.

```python
from agent_core import Registry
from agent_core.mcp import MCPConfig, connect

config = MCPConfig(namespace="notes", url="https://mcp.example/mcp")
async with connect(config) as bridge:
    registry = Registry()
    names = await bridge.register(registry)
    # Compose Runtime with this registry and a host policy, then drive it here.
```

The URL is a placeholder. Authentication headers are host-owned config and are
excluded from repr and tool manifests. HTTPS is required except explicitly
allowed loopback HTTP. Proxy environment and redirects are disabled. Connection
and session lifetime is the async context; registered tools cannot be used after
it closes. Do not retain a runtime beyond its bridge lifetime.

Names use namespace__remote_name and the ordinary Tool name limits. Unsupported
names/schemas fail discovery. Schemas accept the existing bounded Draft 2020-12
subset with local definitions only; external references and rebasing are rejected.
Discovery validates all tools before registration and fails atomically on a
collision, invalid schema, repeated cursor or resource limit. Each tool requires
permission `mcp:namespace__remote_name`, is classified EXTERNAL regardless of
server annotations, and requires approval under the default host policy. The
host must grant both its tool name and permission. Neither the model nor server
metadata grants that authority. Raw SDK session access is a trusted host API;
application tool execution belongs through Runtime, not direct session calls.

Tool versions bind endpoint and server manifest. Host code must recreate the
registry/runtime when the server account, authority or implementation changes.
Never mutate a registered tool's execution semantics under an existing approval.

Configured limits bound discovery tools/pages, individual serialized manifests,
call duration and serialized results. Existing context, argument, output, tool
count and runtime deadline budgets still apply. Result bounds are checked after
SDK decoding; these are not hard process-memory or network-wire limits for MCP.
The host must isolate untrusted servers and enforce network/resource policy.
Timeout/cancellation cannot prove a remote write stopped. Failed dispatched MCP
calls conservatively require reconciliation and are never automatically replayed
by Agent Core. The SDK owns HTTP session mechanics; the bridge does not retry
calls or launch any executable.

References: [protocol lifecycle](https://modelcontextprotocol.io/specification/2025-11-25/basic/lifecycle),
[transport](https://modelcontextprotocol.io/specification/2025-11-25/basic/transports),
[tools](https://modelcontextprotocol.io/specification/2025-11-25/server/tools).
