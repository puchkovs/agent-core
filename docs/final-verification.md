# Historical candidate verification report

This report describes the original candidate. Current extended-release results
are recorded in testing.md and release-readiness.md.

Date: 2026-11-27. Version: 0.1.0a1. Outcome: offline candidate passes its executed
gates; final release remains blocked on live interoperability evidence.

## Correctness and recovery

120 offline tests pass. The branch-aware coverage gate passes overall and for
every critical component. Process-level termination demonstrates recovery from
model-start, saved response, saved dispatch and saved outcome boundaries. Completed
operations are not rerun; unfinished dispatches remain uncertain. Unknown model
usage cannot turn into zero, including after process death.

Approval tests cover canonical arguments, identity, manifest/version, scope,
constraints, expiry, denial and repeated decisions. Invalid, hidden, unauthorized,
escaping and oversized calls do not execute. Invalid batches check cancellation
between calls. Thread timeouts retain the possibility of later side effects.

## Packages and environment

Source and wheel builds succeed. Clean installations with and without HTTP extras
run the original evidence scenario while IP connections are forbidden. Installed
CLI execution succeeds. Wheel Python files match source bytes and include the
typing marker and original local document resources.

Pinned runtime/provider requirements contain 16 independently installed
dependencies; the advisory service returned no known vulnerabilities. Original
project code is MIT; dependent distributions retain their own licenses. Metadata
is recorded separately from any claim of manual legal or source audit.

## Evaluation

100 measured runs after 5 warmups use one integer tool and two scripted responses
with a fresh WAL/FULL database each time. Median end-to-end time is 2.0021885 ms;
nearest-rank p95 is 2.312309 ms. Raw samples and environment are in
[overhead.json](../evaluation/results/overhead.json). The recorded dirty flag is
true because the untracked result directory already existed. The Python source
fingerprint was independently matched to the recorded commit. This is a synthetic
local overhead measurement, not a model score or comparative speed claim.

## Cleanliness and limits

Working files, hidden configuration, all reachable Git blobs, commit messages,
refs and package members were scanned for inappropriate references, sensitive
path patterns and credential patterns. No unresolved finding was returned. Local
Markdown targets resolve. Detailed private audit inputs are not distributed.
This is a bounded text/provenance check, not a proof of authorship or a forensic
certification. Required dependency and authorship notices are preserved.

The package remains a local trusted-host runtime. Live endpoints, remote CI,
provider token streaming, MCP and stronger execution isolation are not verified
features. See [readiness](release-readiness.md) and [security](../SECURITY.md).
