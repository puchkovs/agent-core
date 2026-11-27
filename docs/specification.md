# Execution contract

Status: accepted for implementation, 2026-11-27. Package candidate: 0.1.0a1.
Supported baseline: CPython 3.12 on Linux. All tool execution is sequential.

## Boundaries and public API

`Runtime(model, registry, store, policy, limits)` owns admission and execution.
`create(prompt, session_id=None, output_schema=None)` persists a run and returns
its ID. `resume(run_id)` drives it to a terminal state or a durable pause.
`run(prompt)` is create plus resume. `stream(run_id, after=0)` drives and yields
committed lifecycle events in sequence order. `cancel(run_id)` closes admission.
`approve(run_id, operation_id, binding, actor, allow)` accepts a host decision.
`reconcile(run_id, operation_id, result, actor)` records a host-confirmed outcome;
it never dispatches the operation again. The host authenticates these callers.
The local SDK is not an authenticated server.

Modules: contracts (data), tools (registration/validation), policy (authority),
store (SQLite transactions), context (bounded projection), runtime (orchestration),
providers (wire conversion), CLI (local host). Core imports no provider module.
Session IDs group runs; a new run starts with a new prompt, not implicit shared
conversation or permissions. Instructions remain pinned throughout projection.

## States

created -> running -> completed | failed | cancelled | budget_exceeded
running -> waiting_approval -> running
running -> needs_reconciliation -> running
Completed, failed, cancelled and budget_exceeded are terminal. A recovered running
run with a dispatched operation becomes needs_reconciliation before any action.
A run interrupted during model I/O records unknown usage. Without a token limit
it may repeat that model request; with a token limit it stops conservatively. No tool is
repeated by this path. Terminal resume is read-only.

## Contracts

Messages contain role, content, call IDs, typed tool calls and adapter-owned replay
metadata. Responses contain calls or final text, finish reason and nullable token
usage. Only a complete response can become a persisted assistant message.
Unknown content/stop reasons fail closed at the provider boundary.
A response cannot contain a final output and executable calls simultaneously.
A tool has name, version, input/output schema, effect (read/write/external),
permission set, semantic validator, timeout, output bound and callable.
Identity binding includes a digest of this declared manifest. Changing Python
implementation without changing version is a host contract violation.

Schemas use Draft 2020-12. No external or dynamic references are accepted.
Local references are accepted for generated definitions. Schema rebasing, other
dialects and unresolved local targets are rejected at registration. Schemas are host-owned;
complexity is bounded by registration size and depth. JSON values reject NaN and
infinity. Generated Python contracts use Pydantic strict validation. Providers
may support a smaller schema subset; no universal schema portability is claimed.

## Admission and approval

Order: parse full response -> record calls -> resolve tool -> schema validation ->
semantic validation -> policy -> approval if required -> durable dispatch marker
-> callable -> output validation/bounding -> atomic outcome/context/event commit.
No DB transaction spans external I/O. Unknown tools and rejected input create
matching error observations, without executor access. Explicit policy denial ends
the run. Semantic validators must be pure, trusted host code and cannot grant rights.

Default policy denies everything. Host supplies allowed tool names and permissions.
Writes require approval by default. Binding hashes run ID, operation ID, tool
manifest, canonical argument object, policy scope and run constraints. An approval
has an expiry, actor and a single durable decision; duplicate submissions fail.
Resume recomputes the binding and current policy. Changing scope/manifest/limits
requires a new run; stale approvals do not execute. Model text has no authority.

## Persistence and recovery

SQLite schema version 1; WAL, synchronous FULL, foreign keys, busy timeout.
Run snapshots and operations are materialized records; events are append-only.
The store transaction updates run, operation and associated events together.
Per-run Linux file locks exclude concurrent drivers across store connections and
processes. This is local filesystem coordination, not distributed fencing.
Cancel and approval submissions are independent short transactions.
A crash before dispatch transaction commits has no side effect. After dispatch
commit, missing result is always uncertain, even for a read. This conservative
contract avoids speculative retries. Host reconciliation supplies evidence and
an outcome, or leaves the run blocked. There is no automatic tool retry.

Snapshots retain the current complete model response and next call index. A
committed outcome advances that index in the same transaction, preventing replay
of completed calls, including calls earlier in a paused batch. Event failure
before commit rolls back; consumer failure after commit cannot alter the outcome.

## Budgets, context and retention

Limits: model turns, admitted tool calls, elapsed wall time across pauses,
reported tokens, serialized context bytes, response bytes, arguments bytes,
preview bytes and artifact bytes. Deadline persists as a UTC timestamp; host
clock changes affect restart enforcement. A monotonic per-drive deadline also
bounds active waits. Token budget is checked before and after complete responses;
providers get an output cap. Unknown usage with an enforced token limit fails
closed. Reported usage may exceed remaining budget on the final paid request;
this is an accounting limit, not a billing guarantee.

Context consists of pinned instructions and prompt plus whole completed turn
groups. Drop oldest groups until the configured byte budget fits; never split
call/result groups. Tool schemas and output schema count toward the byte bound.
If pinned data cannot fit, fail before model I/O. Bytes are not model token counts.
Large results become bounded previews with content-addressed SQLite artifacts.
Artifacts and journal remain until the host deletes the DB and its WAL/SHM files;
there is no automatic pruning, encryption or cryptographic audit protection.

## Cancellation and streaming

Cancellation prevents the next model/tool admission. Async functions receive task
cancellation; synchronous functions run in worker threads. A timeout cannot kill
a thread or recall external work. Any interrupted dispatched write is uncertain.
Read cancellation can terminate the run but may leave trusted code finishing.
In-process tools are trusted and must cooperate; isolation requires host processes.

Streaming preserves lifecycle events with bounded cursor pages. Opt-in provider
streaming also journals provisional model.delta records for text, argument and
usage fragments. Deltas cannot authorize execution. Only a validated complete
response after provider terminal events is checkpointed for tool admission.
Missing terminal events and interrupted streams fail with unknown usage and no
tool dispatch. Closing lifecycle streaming requests cancellation and joins the
driver. Direct SDK stream consumers own iterator closure. Total wire/delta byte
limits and existing runtime deadlines apply. Known-secret filtering suppresses
provisional journal writes until the whole response can be checked.

Optional MCP tools enter the same registry, schema checks, policy, approvals and
journal. SDK 1.30.0/protocol 2025-11-25 Streamable HTTP is the selected scope;
server annotations/instructions grant no authority. All discovered tools are
external effects with namespaced permissions and conservative reconciliation.
No process launcher, automatic retry or alternate execution engine is introduced.
See streaming.md and mcp.md for exact limits and verification scope.

## Errors and credentials

Error codes: unknown_tool, invalid_arguments, semantic_rejection, policy_denied,
invalid_output, tool_error, uncertain, cancelled, deadline, turn_limit, tool_limit,
token_limit, unknown_usage, context_limit, provider_auth, provider_rate_limit,
provider_transport, provider_response, refusal, binding_changed and storage_error.
Provider retries are disabled; rate limits expose retryability metadata for host
scheduling. Raw exceptions and HTTP bodies are not persisted. A model-in-flight marker is
committed before the request; missing usage receipts never become zero. Known host secrets
can be redacted from observations before persistence; known values in prompts
or model envelopes are rejected. Callers must not put secrets
in prompts or arguments. SQLite contains task data in plaintext. Credentials live
in provider objects or environment, not snapshots, schemas or event payloads.

## Threat model and acceptance

Untrusted: model output, tool observations and documents. Trusted: host code,
registry, semantic validators, database and local SDK callers. Registry filtering
is presentation only; dispatcher policy is authoritative. Native Python execution
has process authority and is not sandboxed. Workspace examples use restrictive
path rules; concurrent hostile filesystem mutation is outside their threat model.

Acceptance: deterministic offline multitool execution; schema and policy reject
before dispatch; approval tampering/expiry/revocation rejection; crash tests around
intent/result commits; lost-response reconciliation without duplicate effects;
whole-turn projection; bounded outputs; cancellation and slow-reader tests;
provider fixture round trips; at least 90% critical coverage; clean package install.
Live verification is a separate required release gate, never inferred from mocks.
