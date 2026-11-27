"""Run with a freshly installed wheel, outside the source import environment."""

import asyncio
import importlib.util
import json
import socket
import tempfile
from pathlib import Path

import agent_core
from agent_core import Status, Store
from agent_core.scenarios import research

original_connect = socket.socket.connect


def blocked_connect(self, address):
    if self.family in {socket.AF_INET, socket.AF_INET6}:
        raise AssertionError("offline execution attempted network I/O")
    return original_connect(self, address)


socket.socket.connect = blocked_connect
assert "site-packages" in str(Path(agent_core.__file__).resolve())


async def main() -> None:
    with tempfile.TemporaryDirectory() as directory:
        store = Store(Path(directory) / "installed.sqlite")
        try:
            result = await research(store).run("local evidence")
            assert result.status == Status.COMPLETED
            assert json.loads(result.output)["monthly_savings_credits"] == 24
            print(
                json.dumps(
                    {
                        "installed": agent_core.__version__,
                        "offline": True,
                        "httpx_present": importlib.util.find_spec("httpx") is not None,
                    }
                )
            )
        finally:
            store.close()


asyncio.run(main())
