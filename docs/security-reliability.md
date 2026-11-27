# Security and reliability verification

Release 0.1.0, 2026-11-27. This is an engineering report, not a security
certification. The full deterministic suite passes 296 tests with 97.52% combined
statement/branch coverage; every critical runtime, streaming, transport and MCP
component meets the independent 90% gate.

Verified invariants include schema/semantic/policy rejection before dispatch,
operation-specific approval binding and expiry, transaction-time cancellation and
deadline admission, durable dispatch before tool I/O and durable outcome before
observation. Crash/restart tests retain completed outcomes and pause uncertain
operations without automatically replaying their side effects.

Provider streaming requires complete validated terminal envelopes. Tests cover
fragmented arguments, multiple calls, opaque replay blocks, malformed transitions,
missing terminals, disconnects, timeout/cancellation and unknown accounting.
Provisional deltas do not authorize execution. Secret-filtered runtimes suppress
provisional journal writes before whole-envelope validation.

MCP tools pass through the same host policy and approval boundaries. External
classification and namespaced permissions ignore server claims. Controlled local
SDK/HTTP tests verify effects and continuation. No process-launch API is exposed.
MCP size bounds apply after SDK decoding; hard memory/network isolation is outside
this library. The selected SDK retains its own transport behavior and notices.

Source/wheel builds, clean core/provider/MCP installs, installed offline SDK/CLI
smoke, dependency consistency and pinned optional-MCP advisory checks passed.
The advisory service returned no known vulnerabilities for the pinned scope;
results are point-in-time evidence, not comprehensive dependency source review.
History/archive audit checks original ancestry, credential patterns, archive paths,
wheel source bytes, legal notice/typing-marker presence and local documentation.
Pattern scans cannot prove the absence of every possible secret.

Native Python code, SDK callers, semantic validators and local storage are trusted.
There is no hard process sandbox, distributed fencing, authenticated service layer,
arbitrary external exactly-once guarantee, database encryption or automatic data
retention. Deadlines cannot kill threads or recall remote effects. See SECURITY.md,
streaming.md, mcp.md and testing.md for exact boundaries.

Live tool/stream interoperability is verified for one provider scenario only:
Groq `openai/gpt-oss-20b`, complete-response and native-stream modes, 2026-11-27,
four requests, no retries, with a literal-key comparison of the evidence on the
operator's terminal. OpenAI live verification is blocked by account quota.
Anthropic remains experimental and offline-verified. These are single-scenario
smoke results, not a security or broad-quality guarantee. Provider
responses with unknown fields (including returned reasoning text) are rejected,
and a repeated Groq usage receipt is accepted only when its counters are identical.
