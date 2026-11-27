# Contributing

Use Python 3.12 on Linux and install the hash-locked development requirements.
Run `make check` before submitting changes. Add a behavioral regression test for
changes to authority, dispatch, checkpoint, cancellation or replay semantics.
Update the execution specification when guarantees change.

Keep provider translation outside the core, preserve complete call/result groups,
and do not silently retry side effects. New tool implementations must declare
permissions and effect class. A semantic change requires a new tool version.

Use small conventional commits. Never include task databases, credentials,
virtual environments or unrelated files. Normal tests must work offline and
must not call a real model. Live tests require explicit opt-in and cost authority.
