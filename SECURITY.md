# Security model

Agent Core enforces host-declared tool admission; it is not a sandbox or a
security certification. Model content, tool output and documents are untrusted.
The host, registered Python code, local database and SDK caller are trusted.

Policy defaults to deny. A tool must appear in the host allowlist and possess
only granted permissions. Writes require approval unless the host explicitly
changes that default. Approval binds run, operation, canonical arguments, tool
manifest, policy, constraints and expiration. The local CLI has no login layer;
protect access to it and the database using operating-system permissions.

Native functions execute with process rights. Resource limits are admission and
waiting bounds, not CPU, memory or process isolation. A blocking event-loop
coroutine or pathological host-owned validator can prevent timely cancellation.
Run untrusted code in a separately controlled process or container. Threads
cannot be forcibly stopped; interrupted writes are uncertain until reconciled.

File examples restrict operations to a Markdown basename and reject symlinks.
They assume a host-controlled directory without concurrent hostile mutation.
They are not a defense against all filesystem races. No general network, shell,
plugin auto-import, server-provided tools or credential-discovery tool is included.

Provider keys stay in host objects/environment. Raw HTTP error bodies and tool
exceptions are not recorded. `Runtime(secrets=(... ,))` redacts known strings from
tool results and rejects prompts/model envelopes containing those known values.
It is not a universal secret detector. Prompts, arguments, opaque provider replay
metadata, outcomes and artifacts may contain private task data. Avoid credentials
in those fields; protect SQLite, WAL, backups and exported events.

SQLite is plaintext, retained until explicitly removed, and is not a tamper-proof
audit ledger. Per-run file locks coordinate local drivers only. Do not use an
unverified network filesystem or treat this SDK as a multi-tenant server.

For a suspected vulnerability, provide a minimal offline reproducer privately to
the maintainer at puchkov889@gmail.com. Do not include live credentials. No
third-party penetration test or comprehensive vulnerability certification is claimed.
