"""Demonstrate approval, store restart and continuation in a temporary workspace."""

import asyncio
import tempfile
from pathlib import Path

from agent_core import Status, Store
from agent_core.scenarios import workspace


async def main() -> None:
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        path = root / "journal.sqlite"
        store = Store(path)
        runtime = workspace(store, root / "notes")
        run = await runtime.run("Create the planning note")
        assert run.status == Status.WAITING
        assert not (root / "notes" / "plan.md").exists()
        operation = store.operations(run.id)[0]
        runtime.approve(run.id, operation.id, operation.binding, actor="demo-operator")
        store.close()
        store = Store(path)
        try:
            result = await workspace(store, root / "notes").resume(run.id)
            assert result.status == Status.COMPLETED
            assert (root / "notes" / "plan.md").read_text() == "# Plan\nMeasure before expanding.\n"
            assert len(store.operations(run.id)) == 1
            print("Approved operation survived restart; one saved note.")
        finally:
            store.close()


if __name__ == "__main__":
    asyncio.run(main())
