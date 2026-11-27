# Maintenance and next steps

Agent Core 0.1.0 was published on 2026-11-27 as a GitHub Release
([v0.1.0](https://github.com/puchkovs/agent-core/releases/tag/v0.1.0)); the tag points at commit
`e639cb54c19b07363652960cb38a88fe493ace5d`. The repository is public. The package
is not on PyPI. See [release-readiness.md](release-readiness.md) for the recorded
state and [live-verification.md](live-verification.md) for the live procedure.

Constraints for further work: keep Git history intact and never force-push; never
move or re-create the `v0.1.0` tag or replace its published assets (changes ship in
a new version); run `make check` before committing; record actual results in
[testing.md](testing.md) and [progress.md](progress.md).

Possible next work, each needing explicit authorization where it uses quota or
publishes: live OpenAI verification once account quota exists, other Groq models,
Anthropic live verification, and package-index publication. Do not present Groq
results as OpenAI compatibility. All users provide their own API keys; none is
stored in this repository.

To verify the published artifacts independently, rebuild from the tag in a clean
environment (`python -m build`) and compare with `SHA256SUMS` from the release;
the 0.1.0 build was reproducible byte for byte.
