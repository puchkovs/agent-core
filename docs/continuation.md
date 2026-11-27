# Continue development

Continue the existing checkout and history. Do not restore or initialize again.
Origin is the private https://github.com/puchkovs/agent-core repository. The five
original commits remain reachable; baseline HEAD was
`c931cf976fa51e4eb664f529e818c40df2c872d0`. Run `git log -1` for the current audit
commit (the commit cannot contain its own hash). The isolated `.venv` uses the
existing hash-locked requirements; use `make check PYTHON=.venv/bin/python`.

Baseline independently reproduced: 120 tests, 97.53% coverage. Current audit
fixes: 125 tests, 97.54%; lint, format, strict mypy and three demos pass.
Initial remote CI run 45922505014 passed. Inspect later runs before declaring CI
current. See progress.md and roadmap.md for the extended phases 9–16.

Next: finish Phase 9. Investigate strict generated-callable input validation
before dispatch (synchronous and asynchronous callables currently differ),
provider malformed-object handling, cancellation admission races and transport
bounds. Preserve dispatch/outcome persistence and conservative uncertainty.
Then complete provider review, streaming and MCP with behavioral tests, following
the sequential roadmap. Original native streaming/MCP deferrals do not satisfy
the newly requested release scope. Official provider reference pages were opened;
this is not yet a completed compatibility audit.

Do not incur paid provider charges without explicit authority. Keep repository
private. No final release, PyPI publication or history rewrite is authorized.
