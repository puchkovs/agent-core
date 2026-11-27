# Final live verification procedure

Status: **completed 2026-11-27.** Both Groq scenarios passed for
`openai/gpt-oss-20b` at source commit bb2981e: four model requests within the
free-tier allowance (ceiling six), no automatic retry. Sanitized evidence:
[groq-live-verification.json](../evaluation/results/groq-live-verification.json).
Do not rerun under the original allowance; a rerun, or another model, needs new
authorization. The procedure below remains the way to reproduce the check with your
own key. OpenAI live verification was attempted earlier and failed with
`provider_rate_limit` (account billing/quota unavailable); it is not a release gate
and is not claimed.

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

Run from a trusted Ubuntu terminal (paste the whole block). Tracing must be off.
The key is typed at a hidden prompt, never passed as an argument or stored in a
file, and exists only inside a subshell that ends with the block. The script
(1) reads the key, (2) records the source commit, (3) confirms the model is
available to your key via the catalogue endpoint (not a model request),
(4) runs the complete-response scenario, then the native-streaming scenario, with
no retry and a stop on the first failure, (5) validates both evidence files,
(6) checks that the literal key is absent from the evidence and (7) clears the
credential. Normal use is four model requests; the ceiling is six.

```bash
cd ~/Projects/agent-core
(
  set -euo pipefail
  set +x
  umask 077
  MODEL=openai/gpt-oss-20b

  # 1. Secure input: hidden prompt; the key lives only inside this subshell.
  read -rs -p 'Groq API key (hidden): ' GROQ_API_KEY; printf '\n'
  [ -n "$GROQ_API_KEY" ] || { echo 'Empty key; nothing was sent.'; exit 1; }
  export GROQ_API_KEY

  # 2. Evidence directory and source commit (the tree must be committed).
  EVID=$(mktemp -d /tmp/agent-core-live.XXXXXX)
  git rev-parse HEAD > "$EVID/source-commit.txt"
  [ -z "$(git status --porcelain)" ] || echo 'WARNING: working tree is not clean.'

  # 3. Free-tier model check: GET /models is a catalogue call, not a model request.
  .venv/bin/python -I - "$MODEL" <<'PY'
import os, sys, httpx
r = httpx.get("https://api.groq.com/openai/v1/models", timeout=30, follow_redirects=False,
              headers={"Authorization": "Bearer " + os.environ["GROQ_API_KEY"]})
if r.status_code != 200:
    sys.exit("Model listing failed with HTTP %d; no model request was sent." % r.status_code)
ids = {m["id"] for m in r.json()["data"]}
if sys.argv[1] not in ids:
    sys.exit("Model %s is not available to this key; no model request was sent." % sys.argv[1])
print("Model available:", sys.argv[1])
PY

  # 4. Two scenarios, no automatic retry; the first failure stops everything.
  run() {  # $1 = AGENT_CORE_STREAMING, $2 = evidence name
    AGENT_CORE_LIVE=1 AGENT_CORE_GROQ_FREE_TIER=1 AGENT_CORE_PROVIDER=groq \
    AGENT_CORE_MODEL="$MODEL" AGENT_CORE_STREAMING="$1" \
      .venv/bin/python evaluation/live_smoke.py > "$EVID/$2.json" 2> "$EVID/$2.err" \
      || { echo "FAILED: $2 (not retried). Review $EVID/$2.err"; tail -n 5 "$EVID/$2.err"; exit 1; }
    echo "OK: $2"
  }
  run 0 groq-complete
  run 1 groq-streaming

  # 5. Validate evidence: both completed, observation verified, one tool, known usage.
  .venv/bin/python -I - "$EVID" <<'PY'
import json, pathlib, sys
root, turns = pathlib.Path(sys.argv[1]), 0
for name, streaming in (("groq-complete", False), ("groq-streaming", True)):
    e = json.loads((root / (name + ".json")).read_text())
    u = e["usage"]
    assert e["provider"] == "groq" and e["status"] == "completed", name
    assert e["observation_verified"] is True and e["tool_count"] == 1, name
    assert e["native_streaming"] is streaming, name
    assert u["input_tokens"] is not None and u["output_tokens"] is not None, name
    turns += e["model_turns"]
    print(name, e["model"], e["verified_at"], "turns", e["model_turns"], "usage", u)
assert turns <= 6, "request ceiling exceeded"
print("PASS: both Groq scenarios verified; model requests used:", turns)
PY

  # 6. Literal-key leak check (key read from a descriptor, never from argv).
  if grep -rqF -f <(printf %s "$GROQ_API_KEY") "$EVID"; then
    echo 'LEAK: key found in evidence; delete the directory.'; exit 1
  fi
  echo "No key material in evidence. Evidence directory: $EVID"
)
# 7. Credential cleanup: the key never left the subshell; confirm.
unset GROQ_API_KEY; [ -z "${GROQ_API_KEY:-}" ] && echo 'GROQ_API_KEY is not set in this shell.'
```

Evidence records contain provider, model, API profile, UTC date, streaming mode,
model-turn count, tool count, output-token limit and usage; `source-commit.txt`
holds the commit under test. They never contain the key. Copy results into
`docs/testing.md` only after reviewing them.

## Release checklist

- [x] Groq free-tier scope authorized: two scenarios, six requests combined.
- [x] `GROQ_API_KEY` supplied by the operator through a hidden prompt.
- [x] Both Groq live checks passed; evidence validated independently.
- [x] No wire difference required a code change after the live run.
- [x] Offline gates, builds, clean installs and archive audit rerun for 0.1.0.
- [x] Version changed to 0.1.0; release notes written.
- [x] Tag `v0.1.0`, GitHub Release and public visibility completed 2026-11-27.
- [ ] Package-index publication (not done; needs separate authorization).

Successful smoke evidence does not establish broad model quality or every API
feature.
