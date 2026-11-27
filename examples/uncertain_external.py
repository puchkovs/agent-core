"""Demonstrate response loss, an explicit pause, and host reconciliation."""

import asyncio
import json
import tempfile
from pathlib import Path

from agent_core import Status, Store
from agent_core.scenarios import uncertain


async def main() -> None:
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        store = Store(root / "journal.sqlite")
        try:
            runtime = uncertain(store, root / "service")
            run = await runtime.run("Reserve a simulated trial slot")
            operation = store.operations(run.id)[0]
            assert run.status == Status.WAITING
            runtime.approve(run.id, operation.id, operation.binding, actor="demo-operator")
            run = await runtime.resume(run.id)
            assert run.status == Status.UNCERTAIN
            assert (await runtime.resume(run.id)).status == Status.UNCERTAIN
            receipts = (root / "service" / "service-receipts.jsonl").read_text().splitlines()
            assert len(receipts) == 1
            runtime.reconcile(run.id, operation.id, json.loads(receipts[0]), actor="demo-operator")
            assert (await runtime.resume(run.id)).status == Status.COMPLETED
            assert len((root / "service" / "service-receipts.jsonl").read_text().splitlines()) == 1
            print("One simulated remote effect; lost response reconciled without a retry.")
        finally:
            store.close()


if __name__ == "__main__":
    asyncio.run(main())
