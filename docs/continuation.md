# Continuation after v0.1.0 preparation

Continue the existing private origin/main history; preserve the five original
commits and all later work; never force-push. Version 0.1.0 is prepared and
verified, and Groq (`openai/gpt-oss-20b`) is live-verified; see
[release-readiness.md](release-readiness.md) and
[live-verification.md](live-verification.md).

Nothing is tagged or published. Remaining steps need separate authorization:
1. Rebuild `dist/` from the release commit, compare with the SHA-256 values reported
   at preparation time, and re-run `make check`.
2. Create the `v0.1.0` tag, then (if desired) a GitHub Release using
   [release-notes-0.1.0.md](release-notes-0.1.0.md), and any package-index upload.
3. Changing repository visibility from private is a separate decision.

Further work outside this release: live OpenAI verification once quota exists,
other Groq models, and Anthropic live verification. Do not present Groq results as
OpenAI compatibility. All users provide their own API keys; none is stored here.
