"""Subprocess fault fixture: terminate after a committed durability boundary."""

import asyncio
import os
import sys
from pathlib import Path

from agent_core import Call, Effect, Policy, Registry, Response, Runtime, ScriptedModel, Store, Tool

root = Path(sys.argv[1])
mode = sys.argv[2]
store = Store(root / "journal.sqlite")


def effect() -> str:
    with (root / "effects.txt").open("a") as handle:
        handle.write("effect\n")
        handle.flush()
        os.fsync(handle.fileno())
    return "saved"


tool = Tool.from_callable(effect, effect=Effect.EXTERNAL)
model = ScriptedModel(
    (
        Response(calls=(Call(id="c1", name="effect", arguments={}),), finish="tool_calls"),
        Response(text="done"),
    )
)
runtime = Runtime(
    model,
    Registry((tool,)),
    store,
    Policy(allowed_tools=frozenset({"effect"}), approve_writes=False),
)
if mode == "resume":
    run_id = (root / "run-id").read_text()
else:
    run_id = runtime.create("write one simulated receipt")
    (root / "run-id").write_text(run_id)
    original = store.save

    def crash(run, kind, operation=None, data=None):
        original(run, kind, operation, data)
        if kind == mode:
            os._exit(77)

    store.save = crash

try:
    print(asyncio.run(runtime.resume(run_id)).model_dump_json())
finally:
    store.close()
