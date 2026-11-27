# Native provider streaming

Both HTTP adapters accept `streaming=True`. With this option, `complete(request)`
assembles a native stream into a complete Response, and Runtime consumes the
adapter stream inside its existing bounded model request. Without the option,
complete-response HTTP remains the default. `model.stream(request)` always yields
native `ModelDelta` records for SDK users and must be closed when abandoned.

```python
from agent_core.providers.openai_chat import OpenAIChatModel

model = OpenAIChatModel(model_id, api_key, streaming=True)
async for delta in model.stream(request):
    if delta.kind == "text":
        print(delta.text, end="")
    elif delta.kind == "response":
        response = delta.response
```

The example assumes host-supplied model_id, api_key and a typed Request. Direct
SDK consumers own cancellation and iterator closure. Runtime users continue to
use `runtime.stream(run_id)`; it emits durable lifecycle events including
`model.delta` with text/arguments/usage data. Deltas are provisional observations,
not executable tool calls. Only a complete response validated after terminal
framing becomes model.completed and can enter normal tool admission.

OpenAI supports one choice with indexed function-call fragments, optional usage
chunks and a required [DONE] after a finish reason. Anthropic supports ordered
text/client-tool/thinking/redacted-thinking blocks, JSON argument fragments,
usage updates and message_stop after message_delta and all block stops. Unknown
content kinds, unsupported transitions, truncated JSON, invalid argument objects,
duplicate IDs and missing terminal events fail closed. Thinking and signature
blocks remain opaque replay metadata. Server tools and newer profiles are excluded.

Transport bounds total wire bytes, disables redirects/retries, checks SSE content
type and uses configured HTTP read timeouts. Runtime additionally bounds aggregate
delta bytes and total active request time. Usage remains unknown when interrupted;
partial usage does not become a complete accounting receipt. No interrupted tool
proposal is dispatched. Existing recovery and token-budget rules remain in force.

SDK consumption is pull-based with no producer queue. Runtime journals deltas on
disk and lifecycle readers use bounded cursor pages; disk retention remains host
managed. Slow lifecycle readers do not own execution state. Closing the lifecycle
stream requests cancellation and joins its driver. The runtime suppresses provisional
delta persistence when secrets filtering is configured, then checks the assembled
envelope; direct SDK consumers must protect their own output and logs.

Verified offline only against deterministic HTTP streams. No real provider stream
has been called. References: [OpenAI Chat](https://developers.openai.com/api/reference/resources/chat)
and [Anthropic streaming](https://platform.claude.com/docs/en/build-with-claude/streaming).

After explicit quota or cost authority, the existing opt-in live_smoke.py accepts
AGENT_CORE_STREAMING=1 for native streaming. Run it separately for each provider
and also in default complete-response mode; it requires a known usage receipt
and records date, model, API profile and mode. This procedure has not been run live.
