# Final live verification procedure

Status: prepared and tested with offline model substitutes; no paid endpoint has
been called. Run the commands below only after explicit paid-call authorization.

## Credentials and model selection

Supply an OpenAI API key authorized for the chosen model and an Anthropic API key
authorized for its chosen model. Both accounts need available API billing/quota.
Use exact model identifiers available to those accounts. OpenAI must support Chat
Completions, function tools, max_completion_tokens, strict JSON-schema output and
native streaming. Anthropic must support Messages with the adapter's explicit
2023-06-01 profile, client tools and native streaming. No model identifier is
assumed compatible until its live checks pass.

Each check normally makes two model requests: a tool proposal followed by a final
answer after the observation. The host executes sum_integers exactly once with
17 and 25. The tool returns sum 42 and an unpredictable receipt; final structured
output must reproduce both, proving observation handling. Usage must be known.
Evidence includes provider/model/API profile, UTC date, streaming mode, model-turn
count, actual tool count and usage, without API keys.

Each run allows at most three model turns, one tool execution, 60 seconds and 128
requested output tokens per turn. Four checks normally mean eight paid requests;
the configured maximum is twelve requests and 1536 requested output tokens across
all four, plus billable input tokens. These bounds do not guarantee a monetary
cap or prevent provider charges for failed/interrupted requests. Prices depend on
the selected models. No automatic request/tool retry is enabled. A failed check
must be reviewed before any separately authorized rerun.

## Bash commands

Run from a trusted terminal. Supply keys through silent prompts, not command
arguments, source files, shell history or chat. Existing securely injected keys
can be used instead of the two key prompts. Keep terminal tracing disabled.

```bash
cd ~/Projects/agent-core
set +x
umask 077
read -rs -p 'OpenAI API key: ' OPENAI_API_KEY; printf '\n'
read -rs -p 'Anthropic API key: ' ANTHROPIC_API_KEY; printf '\n'
export OPENAI_API_KEY ANTHROPIC_API_KEY
read -r -p 'Exact OpenAI model ID: ' OPENAI_MODEL_ID
read -r -p 'Exact Anthropic model ID: ' ANTHROPIC_MODEL_ID
live_evidence_dir=$(mktemp -d /tmp/agent-core-live.XXXXXX)
git rev-parse HEAD > "$live_evidence_dir/source-commit.txt"
```

OpenAI complete-response execution:

```bash
AGENT_CORE_LIVE=1 AGENT_CORE_PROVIDER=openai AGENT_CORE_MODEL="$OPENAI_MODEL_ID" AGENT_CORE_STREAMING=0 .venv/bin/python evaluation/live_smoke.py > "$live_evidence_dir/openai-complete.json"
```

OpenAI native-streaming execution:

```bash
AGENT_CORE_LIVE=1 AGENT_CORE_PROVIDER=openai AGENT_CORE_MODEL="$OPENAI_MODEL_ID" AGENT_CORE_STREAMING=1 .venv/bin/python evaluation/live_smoke.py > "$live_evidence_dir/openai-streaming.json"
```

Anthropic complete-response execution:

```bash
AGENT_CORE_LIVE=1 AGENT_CORE_PROVIDER=anthropic AGENT_CORE_MODEL="$ANTHROPIC_MODEL_ID" AGENT_CORE_STREAMING=0 .venv/bin/python evaluation/live_smoke.py > "$live_evidence_dir/anthropic-complete.json"
```

Anthropic native-streaming execution:

```bash
AGENT_CORE_LIVE=1 AGENT_CORE_PROVIDER=anthropic AGENT_CORE_MODEL="$ANTHROPIC_MODEL_ID" AGENT_CORE_STREAMING=1 .venv/bin/python evaluation/live_smoke.py > "$live_evidence_dir/anthropic-streaming.json"
```

Require exit status zero for each command and four completed evidence records
with observation_verified=true, tool_count=1 and known usage. Empty or partial
evidence files do not pass. Review each result before proceeding after a failure.
Remove credentials from the terminal environment when finished:

```bash
unset OPENAI_API_KEY ANTHROPIC_API_KEY
printf 'Evidence directory: %s\n' "$live_evidence_dir"
```

## Final release checklist

- [ ] Explicit paid-call authority and access to selected provider models.
- [ ] All four live checks pass; source/model/profile/date/usage evidence reviewed.
- [ ] Confirmed wire differences fixed with deterministic regressions, if needed.
- [ ] Rerun make check, builds, clean core/provider/MCP installs and archive audit
      after any resulting implementation or dependency change.
- [ ] Record final commit, private remote equality and successful current CI.
- [ ] Recheck dependency advisories, documentation, Git integrity and cleanliness.
- [ ] Review final compatibility matrix, security report and version-change approval.
- [ ] Only after mandatory gates pass, prepare the version change and rebuild.
- [ ] Obtain separate authorization for any final release/tag, GitHub Release,
      public repository visibility change or PyPI publication.

Version remains 0.1.0a1 until the mandatory live gate succeeds. Keeping successful
smoke evidence does not establish broad model quality or every API feature.
