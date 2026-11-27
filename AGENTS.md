# Engineering instructions

Maintain explicit execution contracts and deny by default. Persist dispatch
before I/O and outcome before observation. Never automatically replay uncertain
operations. Keep model context separate from host authority. Add behavioral tests
for changed guarantees. Run `make check` before committing verified changes.
Update docs/progress.md and docs/testing.md with actual results and next work.
Keep the project independent, with its own source and Git history. Preserve
required legal notices for actual dependencies. Never commit credentials,
private task databases, caches, virtual environments or unrelated materials.

The repository is public and v0.1.0 is published as a GitHub Release. Never move,
delete or re-create the `v0.1.0` tag or replace its release assets; fixes ship in
a new version. Never rewrite history or force-push; the original commits are
preserved. Push to the remote only when authorized.

Paid or quota-limited provider calls, package-index publication, new tags or
releases and visibility changes require explicit authorization. Provider keys come
from the host environment only and are never written to files, logs, evidence or
chat. Keep docs/roadmap.md and docs/release-readiness.md consistent with recorded
evidence, and claim no provider compatibility beyond it.
