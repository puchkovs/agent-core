# Verification

Foundation verification (2026-11-27, CPython 3.12.14, Linux):

- `ruff check src tests`: passed.
- `ruff format --check src tests`: formatting applied, final gate still pending.
- `mypy src`: passed, strict mode, 8 source modules.
- `pytest -q`: 47 tests passed.

Tests exercise denial before dispatch, invalid arguments, approvals across restart,
expiry, changed authority, persisted outcomes, unknown side effects, reconciliation,
cancellation, time/token/iteration/tool limits, context grouping and event cursors.
Provider, build/install, dependency and final release gates remain pending.
