# Final live verification procedure

Status: prepared and tested offline. **No live Groq request has been sent.** The
execution environment of the prior sessions did not inherit `GROQ_API_KEY`, so the
two checks below must be run from a trusted local terminal that holds the key.
Groq live verification is authorized only within the free-tier quota: at most six
model requests combined, no automatic retries. Do not start either command more
than once under this allowance. OpenAI live verification was attempted earlier and
failed with `provider_rate_limit` (account billing/quota unavailable); it is not a
release gate and is not claimed.

## Credentials and model selection

Groq accepts the OpenAI Chat Completions wire format at
`https://api.groq.com/openai/v1/chat/completions`. The release gate uses
`openai/gpt-oss-20b`: a production-listed model with local function tool use, native
streaming, and a free-plan allowance of 30 requests/minute, 1,000 requests/day,
8,000 tokens/minute and 200,000 tokens/day (per the Groq rate-limits page reviewed
2026-11-27; limits can change, check your own limits page). The same profile also
encodes `openai/gpt-oss-120b` and `qwen/qwen3.8-27b`; no claim is made for them
until separately run. Each user supplies their own `GROQ_API_KEY`.

Each check normally makes two model requests: a tool proposal followed by a final
answer after the observation. The host executes `sum_integers` exactly once with
17 and 25. The tool returns the sum 42 and an unpredictable receipt; the final JSON
must reproduce both, proving observation handling. Usage must be known.

Each run allows at most three model turns, one tool execution, 60 seconds and 512
requested output tokens per turn (Groq reasoning tokens count against
`max_completion_tokens`; the adapter requests `low` effort and hides reasoning).
The two checks normally mean four requests; the configured ceiling is six requests
and 3,072 requested output tokens across both. No automatic request/tool retry is
enabled. A failed check must be inspected before any separately authorized rerun.

`AGENT_CORE_GROQ_FREE_TIER=1` is your confirmation that the key belongs to a
free-plan organization; the script refuses to run without it.

## Bash commands

Run from a trusted terminal. Supply the key through a silent prompt, not a command
argument, source file, shell history or chat. An already securely injected
`GROQ_API_KEY` can be used instead of the prompt. Keep terminal tracing disabled.

```bash
cd ~/Projects/agent-core
set +x
umask 077
read -rs -p 'Groq API key: ' GROQ_API_KEY; printf '\n'
export GROQ_API_KEY
live_evidence_dir=$(mktemp -d /tmp/agent-core-live.XXXXXX)
git rev-parse HEAD > "$live_evidence_dir/source-commit.txt"
```

Groq complete-response execution:

```bash
AGENT_CORE_LIVE=1 AGENT_CORE_GROQ_FREE_TIER=1 AGENT_CORE_PROVIDER=groq AGENT_CORE_MODEL=openai/gpt-oss-20b AGENT_CORE_STREAMING=0 .venv/bin/python evaluation/live_smoke.py > "$live_evidence_dir/groq-complete.json"
```

Groq native-streaming execution:

```bash
AGENT_CORE_LIVE=1 AGENT_CORE_GROQ_FREE_TIER=1 AGENT_CORE_PROVIDER=groq AGENT_CORE_MODEL=openai/gpt-oss-20b AGENT_CORE_STREAMING=1 .venv/bin/python evaluation/live_smoke.py > "$live_evidence_dir/groq-streaming.json"
```

Require exit status zero for each command and two completed evidence records with
`observation_verified=true`, `tool_count=1`, `status=completed` and known usage.
Empty or partial evidence files do not pass. Remove the credential when finished:

```bash
unset GROQ_API_KEY
printf 'Evidence directory: %s\n' "$live_evidence_dir"
```

Evidence records contain provider, model, API profile, UTC date, streaming mode,
model-turn count, tool count, output-token limit and usage; `source-commit.txt`
holds the commit under test. They never contain the key. Copy results into
`docs/testing.md` only after reviewing them.

## Final release checklist

- [x] Groq free-tier scope authorized: two scenarios, six requests combined.
- [ ] `GROQ_API_KEY` available to the executing process (blocked in prior sessions).
- [ ] Both Groq live checks pass; source/model/profile/date/usage evidence reviewed.
- [ ] Confirmed wire differences fixed with deterministic regressions, if needed.
- [ ] Rerun `make check`, builds, clean core/provider/MCP installs and archive audit
      after any resulting implementation or dependency change.
- [ ] Record final commit, private remote equality and successful current CI.
- [ ] Recheck dependency advisories, documentation, Git integrity and cleanliness.
- [ ] Review final compatibility matrix, security report and version-change approval.
- [ ] Only after mandatory gates pass, change the version to 0.1.0 and rebuild.
- [ ] Obtain separate authorization for any final release/tag, GitHub Release,
      public repository visibility change or PyPI publication.

Version remains 0.1.0a1 until the mandatory live gate succeeds. Keeping successful
smoke evidence does not establish broad model quality or every API feature.
