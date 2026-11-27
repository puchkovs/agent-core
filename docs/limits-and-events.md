# Limits, context, events and retention

`Limits` bounds turns, dispatched tools, elapsed seconds, reported tokens,
serialized context/response/argument bytes, preview bytes and artifact bytes.
Tool timeouts may be stricter than the run deadline. Pauses count toward elapsed
time. Deadlines use persisted wall time and active monotonic waits; host clock
changes affect restart enforcement.

Token limits use provider-reported input/output usage. Unknown usage with a
configured token budget stops admission. The runtime caps requested output tokens
and checks total usage after a full response. Input usage and interrupted or
rejected responses may not be known; this is not a hard monetary spending cap.

Context projection keeps instructions and prompt plus complete assistant/tool
turn groups, dropping oldest whole groups when necessary. It counts schemas,
metadata and output constraints as serialized bytes. Bytes do not replace a
provider-specific tokenizer. If pinned data cannot fit, no model request starts.
The full journal and all approvals survive projection trimming.

Tool results are JSON serialized and optionally redacted before storage. Large
results get a strictly bounded metadata/preview envelope and a content-addressed
SQLite artifact. Read it through the host store/CLI; a model does not receive an
implicit unrestricted artifact-reading tool. Oversized artifacts are rejected as
`output_limit`. Python tools may allocate large objects before returning; the
runtime does not impose process-memory limits.

Events have database sequence, run ID, timestamp, kind, optional operation ID and
bounded lifecycle metadata. Outcomes and state events commit together. Policy
decisions are visible before dispatch. Tool records contain durations; model
completion events record durations and reported usage.

`stream` uses bounded pages from SQLite, without a subscriber callback on the
execution path or an in-memory unbounded queue. Slow consumers lag on disk;
closing the stream requests cancellation and joins the driver. Events can be
read again by cursor. Opt-in native streaming adds provisional model.delta events;
only complete validated envelopes can authorize tool admission. There are no
network event acknowledgments, automatic retention or guaranteed delivery to a
disconnected consumer. See [native streaming](streaming.md).

Snapshots, events, artifacts and WAL backups persist until host removal. Keep
active databases outside the checkout. Back up SQLite consistently using its
backup interface or after clean shutdown; do not copy only a live main DB file.
No automatic deletion, encryption, compression or multi-tenant artifact ACLs are
provided. Treat exported events and database files as private task data.
