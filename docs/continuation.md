# Continue OpenAI release verification

Continue the existing private origin/main history; preserve the five original
commits and all subsequent work. Reviewed starting HEAD: f1002640f7826f1787115bc9114b19ac8a68c767.
Use git log -1 for current HEAD. Version remains 0.1.0a1 until the revised gates pass.

The user authorizes paid OpenAI requests exclusively for non-streaming and native
streaming tool/receipt scenarios, at most six model requests combined, without
automatic retries. OPENAI_API_KEY currently is not inherited by either execution
shell. Asked the user to expose it securely to the running session; never paste or
print the value. Zero paid requests have been sent. Recheck presence only after
an environment update. Do not consume this allowance on other generation tasks.

Use evaluation/live_smoke.py once with AGENT_CORE_PROVIDER=openai and streaming=0,
then once with streaming=1, each capped at three turns. Verify dynamic tool use,
one execution, exact sum/unpredictable receipt and known usage. Capture safe
model/profile/date/token evidence; inspect any failure without automatic replay.
No live model compatibility is established yet. Select an accessible low-cost
model against current official documentation before sending a request.

Anthropic credentials will not be supplied. Anthropic is experimental and
offline-verified, not live-verified; preserve its implementation/tests. Its live
verification is no longer a mandatory v0.1.0 gate. All users provide their own keys.

Rerun offline gates/builds/clean installs/audits, update compatibility/changelog,
and prepare v0.1.0 only if both OpenAI checks pass. Keep repository private; no
GitHub Release or PyPI publication. Paid authorization need not be requested again.
