"""Explicitly opt-in paid endpoint smoke. Never run automatically in normal CI.

Set AGENT_CORE_LIVE=1, AGENT_CORE_PROVIDER=openai|anthropic,
AGENT_CORE_MODEL and the corresponding OPENAI_API_KEY or ANTHROPIC_API_KEY.
This sends a real request and may incur provider charges.
"""

import asyncio
import json
import os
import tempfile
from pathlib import Path

from agent_core import Policy, Registry, Runtime, Status, Store, Tool


async def main() -> None:
    if os.environ.get("AGENT_CORE_LIVE") != "1":
        raise SystemExit("Live testing disabled; explicit AGENT_CORE_LIVE=1 required.")
    provider = os.environ["AGENT_CORE_PROVIDER"]
    model_id = os.environ["AGENT_CORE_MODEL"]
    effects = []

    def sum_integers(left: int, right: int) -> int:
        """Add two integers and return their sum. Use this tool for the requested arithmetic."""
        effects.append((left, right))
        return left + right

    if provider == "openai":
        from agent_core.providers.openai_chat import OpenAIChatModel

        key = os.environ["OPENAI_API_KEY"]
        model = OpenAIChatModel(model_id, key)
    elif provider == "anthropic":
        from agent_core.providers.anthropic import AnthropicModel

        key = os.environ["ANTHROPIC_API_KEY"]
        model = AnthropicModel(model_id, key)
    else:
        raise SystemExit("Only openai or anthropic is supported.")
    tool = Tool.from_callable(sum_integers)
    with tempfile.TemporaryDirectory() as directory:
        store = Store(Path(directory) / "live.sqlite")
        try:
            runtime = Runtime(
                model,
                Registry((tool,)),
                store,
                Policy(allowed_tools=frozenset({"sum_integers"})),
                secrets=(key,),
            )
            run = await runtime.run(
                "Call sum_integers once with left=17 and right=25, then answer with the sum."
            )
            assert run.status == Status.COMPLETED, run.reason
            assert effects == [(17, 25)], effects
            assert "42" in str(run.output)
            print(
                json.dumps(
                    {
                        "provider": provider,
                        "model": model_id,
                        "status": run.status,
                        "tool_count": run.tool_count,
                        "usage": run.usage.model_dump(),
                    },
                    indent=2,
                )
            )
        finally:
            store.close()


if __name__ == "__main__":
    asyncio.run(main())
