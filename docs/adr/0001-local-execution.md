# ADR 1: Local sequential execution and conservative recovery

Accepted, 2026-11-27.

Use a sequential run driver and SQLite transactions. Save batch responses before
admission, and commit outcomes and cursors together. Mark any interrupted dispatch
uncertain. Recovery never guesses whether a remote write happened and never
repeats it automatically. Host reconciliation supplies confirmed results.

This sacrifices automatic read retry and concurrent throughput for simpler,
verifiable recovery. Distributed ownership and automated reconciliation are
future contracts, not implied by the local journal.
