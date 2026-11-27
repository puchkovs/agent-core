"""Run from an installed checkout: python examples/offline_research.py."""

import asyncio
import json
import tempfile
from pathlib import Path

from agent_core import Status, Store
from agent_core.scenarios import research


async def main() -> None:
    with tempfile.TemporaryDirectory() as directory:
        store = Store(Path(directory) / "research.sqlite")
        try:
            run = await research(store).run("Estimate lighting savings using the local evidence.")
            assert run.status == Status.COMPLETED
            output = json.loads(run.output)
            assert output["daily_savings_kwh"] == 6
            assert output["monthly_savings_credits"] == 24
            print(json.dumps(output, indent=2))
        finally:
            store.close()


if __name__ == "__main__":
    asyncio.run(main())
