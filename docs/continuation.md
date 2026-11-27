# Continue development

Continue the existing checkout and history. Do not restore or initialize again.
Origin is the private https://github.com/puchkovs/agent-core repository. The five
original commits remain reachable; baseline HEAD was
`c931cf976fa51e4eb664f529e818c40df2c872d0`. Run `git log -1` for the current audit
commit (the commit cannot contain its own hash). The isolated `.venv` uses the
existing hash-locked requirements; use `make check PYTHON=.venv/bin/python`.

Baseline independently reproduced: 120 tests, 97.53% coverage. Current audit
fixes: 127 tests, 97.56%; lint, format, strict mypy and three demos pass.
Initial remote CI run 45922505014 passed. Inspect later runs before declaring CI
current. See progress.md and roadmap.md for the extended phases 9–16.

Next: finish Phase 9. Strict generated-callable input validation now runs before dispatch for
both synchronous and asynchronous tools. Next investigate provider malformed-object
handling, cancellation admission races, transport bounds and remaining audit areas. Preserve dispatch/outcome persistence and conservative uncertainty.
Then complete provider review, streaming and MCP with behavioral tests, following
the sequential roadmap. Original native streaming/MCP deferrals do not satisfy
the newly requested release scope. Official provider reference pages were opened;
this is not yet a completed compatibility audit.

Do not incur paid provider charges without explicit authority. Keep repository
private. No final release, PyPI publication or history rewrite is authorized.

## Audit installation verification

Implementation commit `57b7b0b60bf71f3ef0c8489bca6471b332f5a572` was pushed and
matched remote main. `git fsck --full` passed. Updated source/wheel builds passed
using hatchling 1.33.0. Clean minimal installation passed installed SDK smoke
with IP network connections blocked and no httpx installed; installed CLI demo
completed. Installing the hash-locked provider dependencies into that clean
environment also passed `pip check` and the installed offline SDK smoke with
httpx present. Distributions remain ignored under dist/ and are alpha artifacts.

Current implementation CI: run 45922819563; inspect its final conclusion using
`gh run view 45922819563`. Earlier baseline and mutation-fix CI runs passed.
These checks do not complete the extended phases 9–16 or establish native
streaming/MCP compatibility. Live verification and the full release gate remain
unpassed. Continue Phase 9 from docs/continuation.md.
