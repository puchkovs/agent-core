# ADR 2: Authority is separate from conversation

Accepted, 2026-11-27.

Bind approvals to exact call, tool manifest, policy and limits. Revalidate at
resume. Persist approval decisions independently from messages. Model context
contains entire completed groups and pinned instructions, but cannot modify the
policy. Projection trimming therefore cannot elevate authority.

The host must version changed tool implementations and authenticate approval
callers. Native functions remain trusted process code.
