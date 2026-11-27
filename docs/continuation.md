# Restore and continue

The handoff archive contains `agent-core/` with complete `.git` history. Extract
into an empty directory, then move that folder to `~/Projects/agent-core` if desired.
Do not overwrite another checkout. A separate Git bundle is also supplied.

```sh
cd ~/Projects/agent-core
git status --short
git fsck --full
python3 -m venv .venv
. .venv/bin/activate
pip install --require-hashes -r requirements-dev.lock
pip install -e . --no-deps
make check
```

Alternative restoration from the bundle, into a new directory:

```sh
git clone /path/to/agent-core.bundle agent-core
cd agent-core
git remote remove origin
```

The bundle represents this project's independent local history, not a remote
publication. Check the final handoff report for the exact included commit and
verification results. Keep existing run databases outside the checkout.

Next engineering task: obtain explicit cost authority and an appropriate API key
through the host environment; select a model ID and run the opt-in live smoke.
Record the date, provider profile, model, real tool invocation and usage. Fix any
wire differences with regression fixtures and rerun `make check`. Repeat for the
second profile before claiming live support for it.

After those gates, update compatibility and readiness documents, rebuild and
verify clean installations, rerun the complete cleanliness/package audit, then
prepare a final v0.1.0 release. Remote publication remains a separate authorized
action. MCP remains deferred unless a later task supplies a verifiable versioned
SDK, transport and lifecycle conformance scope.
