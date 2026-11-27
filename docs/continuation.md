# Continue Groq release verification

Continue the existing private origin/main history; preserve the five original
commits and all subsequent work. Use `git log -1` for the current HEAD. Version
remains 0.1.0a1 until the revised gates pass. Do not push, tag or publish without
explicit authorization.

The Groq profile (`src/agent_core/providers/groq.py`) is implemented and
offline-verified. **Zero live requests have been sent.** `GROQ_API_KEY` was not
inherited by the execution shell; never ask for it in chat. The author runs the two
checks from a local terminal with the commands in
[live-verification.md](live-verification.md): `AGENT_CORE_PROVIDER=groq`,
`AGENT_CORE_MODEL=openai/gpt-oss-20b`, `AGENT_CORE_GROQ_FREE_TIER=1`, once with
`AGENT_CORE_STREAMING=0` and once with `1`, at most six requests combined, no
automatic retry. Recheck key presence only after an environment update.

After the two evidence files exist: review them, record model/profile/date/usage
and source commit in docs/testing.md, fix any confirmed wire difference with a
deterministic regression, rerun `make check` (use `PYTHON=.venv/bin/python`),
builds, clean installs and the history/archive audit, then change the version to
0.1.0, update README/changelog/compatibility matrix, rebuild, commit and (with
authorization) push to the private origin and verify CI.

OpenAI is offline-verified; live verification is blocked by account quota and is
not a gate. Anthropic is experimental and offline-verified. Successful Groq results
must not be presented as OpenAI API compatibility. All users provide their own keys.
