# Model providers

| Adapter | Implemented contract | Verification | Not supported |
|---|---|---|---|
| `ScriptedModel` | Complete envelopes indexed by durable turn | Offline unit/E2E | Model intelligence claims |
| `OpenAIChatModel` | HTTPS Chat Completions, text, client function calls, usage, JSON schema request | Mock HTTP round trips and runtime fixtures | Responses API, audio, images, server tools, token deltas |
| `AnthropicModel` | HTTPS Messages, explicit `2023-06-01` header, text/client-tool blocks, usage, opaque thinking replay | Mock HTTP round trips and runtime fixtures | Newer version profiles, server tools, token deltas |

**No real model endpoint was called for this candidate.** Fixture verification
proves normalization behavior for the supplied shapes, not live service support.
No model name or general compatible-server claim is implied by these adapters.

Install the `providers` extra, then instantiate an adapter with a host-provided
model ID and API key. Credentials are not part of serialized execution state.

```python
import os
from agent_core.providers.openai_chat import OpenAIChatModel

model = OpenAIChatModel(os.environ["AGENT_CORE_MODEL"], os.environ["OPENAI_API_KEY"])
```

Both adapters reject incomplete/non-success stop reasons, malformed calls,
duplicate call IDs and unsupported content. Provider-owned replay metadata stays
with its originating adapter and cannot be replayed into the other contract.
OpenAI can request native JSON schema output; the model/endpoint must support that
schema subset. Anthropic receives a final-JSON instruction and relies on runtime
validation; native structured output is not advertised for this profile.

Transport reads bounded complete JSON responses over HTTPS, does not follow
redirects and has no automatic retries. HTTP auth, rate limit, service and
transport failures are classified separately. Retryability is a host scheduling
signal, not permission to repeat tools. Rate-limit backoff and provider fallback
are not automatic in this candidate. Unknown usage remains null, not zero.

The adapter assumptions were checked against official API documentation:
[OpenAI Chat](https://developers.openai.com/api/reference/resources/chat) and
[Anthropic Messages](https://platform.claude.com/docs/en/api/messages/create).
The current Anthropic reference describes newer profiles too; this package does
not claim that its older selected profile has been live-verified.

## Opt-in live gate

`evaluation/live_smoke.py` is excluded from normal tests. It requires
`AGENT_CORE_LIVE=1`, `AGENT_CORE_PROVIDER`, `AGENT_CORE_MODEL` and the corresponding
key. It may incur real charges. After explicit cost authority, run it separately
for each selected model and preserve the model ID, API profile, date and outcome.
The test requires one arithmetic tool call and checks the returned sum. A single
successful smoke is not broad task-quality or safety validation.
