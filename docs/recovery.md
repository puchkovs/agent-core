# Sessions, approvals and recovery

A session groups runs for host bookkeeping. A new run does not automatically
receive previous messages, permissions or approvals. A run stores prompt,
instructions, configuration digest, deadline, usage, complete turn groups and a
pending-response cursor. SQLite schema version 1 is created transactionally;
unknown schema versions are rejected. There is no upgrade from a prior release.

## Approval

A paused run has a `prepared` operation with exact arguments, binding and expiry.
Submit `runtime.approve(run_id, operation_id, binding, actor="operator")` from
a trusted host interface. Actor is audit metadata; this library does not
authenticate the string. Denials and repeated/stale/expired decisions fail closed.
Call `resume` after a durable decision. Configuration changes invalidate the run;
create a new run for new authority. There is no implicit reapproval migration.

## Crash boundaries

| Last committed boundary | Restart behavior |
|---|---|
| Run created, no model response | Use current durable turn; interrupted requests have unknown usage |
| Complete model envelope | Process saved response, including a final answer |
| Prepared operation | Revalidate and obtain/check approval before admission |
| Dispatched operation, no outcome | Pause as `needs_reconciliation`; do not retry |
| Outcome and cursor | Reuse result; continue at the next call |
| Final state | Return saved state without executing tools |

SQLite cannot atomically commit a remote service action. A dispatched operation
may not have started, may be running, or may have completed when a process dies.
This runtime chooses uncertainty for all interrupted dispatches, including reads.

## Reconciliation

Confirm the remote receipt or actual resource state through a trusted host path.
Ensure a timed-out local worker cannot still mutate it. Then call:

```python
runtime.reconcile(run_id, operation_id, {"receipt": "confirmed-id"}, actor="operator")
result = await runtime.resume(run_id)
```

Reconciliation records a supplied successful outcome and advances the saved call
cursor; it never retries the tool. If no outcome can be confirmed, leave the run
blocked. Explicit failure/compensation reconciliation is a future extension.

One driver per run is enforced through a Linux file lock. Cancellation and
approval decisions use short independent SQLite transactions. This is not
distributed ownership or multi-host fencing. Database errors propagate and may
require host repair; they must not cause an automatic tool retry.
