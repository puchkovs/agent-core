# Local CLI

All commands accept `--db PATH`. `demo`, `resume`, `stream` and `reconcile` also
use a host scenario: `--scenario research|workspace|uncertain`. The latter two
require `--workspace PATH`. Use the same scenario and workspace on continuation.
Changing the declared scope causes `binding_changed`.

| Command | Behavior |
|---|---|
| `demo` | Create and drive the selected original offline scenario |
| `show RUN_ID` | Print saved run and operations, including approval bindings |
| `events RUN_ID` | Print committed events as JSON lines |
| `stream RUN_ID` | Drive the run and emit ordered lifecycle events |
| `cancel RUN_ID` | Durably request cancellation; active driver stops admission |
| `approve RUN_ID OP_ID BINDING --actor NAME` | Save an approval decision |
| `approve ... --deny` | Save a denial |
| `resume RUN_ID` | Continue from the saved response/call cursor |
| `reconcile RUN_ID OP_ID RESULT_JSON --actor NAME` | Record a confirmed outcome |
| `artifact HASH --offset N --limit N` | Read a bounded artifact character range |

Example workflow, using IDs and binding from `show`:

```sh
agent-core --db notes.sqlite --scenario workspace --workspace ./notes demo
agent-core --db notes.sqlite show "$RUN_ID"
agent-core --db notes.sqlite approve "$RUN_ID" "$OP_ID" "$BINDING" --actor operator
agent-core --db notes.sqlite --scenario workspace --workspace ./notes resume "$RUN_ID"
```

Set the shell variables to the exact displayed values; they are not inferred
from conversation text. Exit status is 0 for successful commands and durable
pauses, 1 for failed/budget/cancelled driven runs, and 2 for command errors.
`cancel` records a request, not proof that an already dispatched effect stopped.

The CLI intentionally does not load arbitrary Python plugins or run a model
endpoint automatically. Use the SDK for application-specific host composition and
`evaluation/live_smoke.py` for explicit opt-in endpoint verification.
