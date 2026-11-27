# Model providers

| Adapter | Implemented contract | Verification | Not supported |
|---|---|---|---|
| `ScriptedModel` | Complete envelopes indexed by durable turn | Offline unit/E2E | Model intelligence claims |
| `OpenAIChatModel` | HTTPS Chat Completions, text, client function calls, usage, JSON schema request | Mock HTTP round trips and runtime fixtures | Responses API, audio, images, server tools |
| `GroqModel` | OpenAI-compatible Chat Completions profile for Groq: text, client function calls, native streaming, usage, final-JSON instruction with host validation | Offline fixtures; live-verified for `openai/gpt-oss-20b` only | Native JSON-schema output, parallel tool calls, built-in/remote server tools, returned reasoning text |
| `AnthropicModel` (experimental) | HTTPS Messages, explicit `2023-06-01` header, text/client-tool blocks, usage, opaque thinking replay | Offline fixtures only; not live-verified | Newer version profiles, server tools |

**Live evidence exists for exactly one profile:** Groq with `openai/gpt-oss-20b`,
non-streaming and native streaming, on 2026-11-27 ([evidence](../evaluation/results/groq-live-verification.json)).
Earlier OpenAI attempts failed with `provider_rate_limit` (account quota), so OpenAI
and Anthropic rest on fixture verification, which proves normalization behavior for
the supplied shapes, not live service support.
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

## Provider contract review — 2026-11-27

Reviewed the [OpenAI Chat reference](https://developers.openai.com/api/reference/resources/chat),
[Messages reference](https://platform.claude.com/docs/en/api/messages/create) and
[Anthropic cache accounting](https://platform.claude.com/docs/en/build-with-claude/prompt-caching).
The current Messages reference defaults to a newer API profile; this adapter
continues to send its explicit 2023-06-01 header. No newer-profile compatibility
or model-specific capability is inferred from that reference.

Token counters must be nonnegative integers; strings, booleans and fractions are
rejected. Anthropic input usage includes uncached, cache-creation and cache-read
input tokens. Missing accounting stays unknown; cache fields absent from the
selected legacy profile contribute zero, while explicit null stays unknown.
OpenAI prompt_tokens already represents its total input count. Raw provider
usage and selected response identity metadata are preserved separately from
normalized usage, alongside existing adapter-specific message replay data.
Malformed response objects produce provider_response; falsy nontext content is
rejected. Refusal values must be strings or null.

Both adapters retain configurable model IDs and HTTPS endpoints. An injected
HTTP client remains caller-owned; Agent Core closes clients it creates. Redirects
and retries stay disabled. Wire responses reject duplicate JSON keys, including
nested objects. Native structured output remains OpenAI request-level support
for compatible models; Anthropic uses final-JSON instructions plus host schema
validation. No universal schema portability or live compatibility is claimed.

OpenAI live verification was attempted and failed with provider_rate_limit; it
remains blocked on account quota. Anthropic remains experimental and
offline-verified. Use the opt-in live_smoke.py only after cost/quota authority is
granted; do not put API keys in evidence files. Native token streaming is fixture-verified; see streaming.md.

Native streaming is now available with streaming=True; see [streaming](streaming.md)
for exact fixture-verified scope. Earlier token-delta deferrals describe the historical candidate.

The final live gate now verifies the exact sum and an unpredictable receipt from
the tool observation, with known usage. See [secure live commands and release
checklist](live-verification.md) for the two mandatory Groq modes and configured request limits.

## Groq profile — reviewed 2026-11-27

`GroqModel` subclasses the OpenAI Chat adapter and sends the same wire format to
`https://api.groq.com/openai/v1/chat/completions`; complete-envelope validation,
SSE framing, call assembly and the no-partial-dispatch rule are shared, not copied.
A configuration-only profile was insufficient, so the subclass changes exactly what
the [Groq documentation](https://console.groq.com/docs/openai) requires:

| Topic | Behavior |
|---|---|
| Tool calling | Local function tools on all listed models; `parallel_tool_calls` is sent as `false` (gpt-oss does not support parallel calls) and the runtime stays sequential |
| Streaming | Native SSE; tool calls are dispatched only after the assembled response validates |
| Structured output | Groq documents that JSON-schema output is unavailable with tool use and streaming, so no `response_format` is sent; the final-JSON instruction is added and the host validates the result. No endpoint schema guarantee is claimed |
| Reasoning | `include_reasoning=false` plus `reasoning_effort` (`low` for gpt-oss-20b/120b, `none` for qwen3.8-27b) only for those documented models; other models receive neither parameter. Returned reasoning fields are rejected as unsupported content, not replayed |
| Usage | Read from `x_groq.usage` (or top-level `usage`); a repeated receipt is accepted only when prompt, completion and total counters are identical, never summed. Missing usage stays unknown. OpenAI keeps rejecting any duplicate receipt |
| Finish reasons | `stop` and `tool_calls` only; `length` and others are rejected as incomplete |
| Unsupported fields | `messages[].name`, `logprobs`, `logit_bias`, `top_logprobs` and `n>1` are never sent |
| Errors | 401/403 `provider_auth`; 429 `provider_rate_limit` (retryable signal, no automatic retry); 5xx `provider_unavailable`; other statuses, including 400 failed generations, 413, 422, 424, 498 and 499, `provider_response` |

Free-plan limits listed on the Groq rate-limits page for `openai/gpt-oss-20b`,
`openai/gpt-oss-120b` and `qwen/qwen3.8-27b`: 30 requests/minute, 1,000 requests/day,
8,000 tokens/minute, 200,000 tokens/day. Reasoning tokens count against
`max_completion_tokens`, so choose a limit that covers hidden reasoning. The model
list and limits change; consult your own account limits page.

```python
import os
from agent_core.providers.groq import GroqModel

model = GroqModel("openai/gpt-oss-20b", os.environ["GROQ_API_KEY"], streaming=True)
```

## Compatibility matrix

| Provider | Non-streaming | Native streaming | Status |
|---|---|---|---|
| Groq | Live-verified (`openai/gpt-oss-20b`) | Live-verified (`openai/gpt-oss-20b`) | Live-verified for that model and scenario; other Groq models offline only |
| OpenAI | Offline fixtures | Offline fixtures | Live verification blocked by API rate limit/quota |
| Anthropic | Offline fixtures | Offline fixtures | Experimental |

## v0.1.0 acceptance

Groq non-streaming and native-streaming tool/receipt verification within the free
tier was mandatory and passed for `openai/gpt-oss-20b` (four model requests, no
retries). OpenAI is offline-verified; its live verification is blocked by account
quota and was not a gate. Anthropic remains experimental and offline-verified.
Groq results never imply original OpenAI API compatibility, and no other model is
live-verified. Each user supplies their own credentials through the host
environment; the project never ships maintainer credentials.
