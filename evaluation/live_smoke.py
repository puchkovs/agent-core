"""Explicitly opt-in paid endpoint smoke. Never run automatically in normal CI.

Set AGENT_CORE_LIVE=1, AGENT_CORE_PROVIDER=openai|anthropic|groq,
AGENT_CORE_MODEL and the corresponding OPENAI_API_KEY, ANTHROPIC_API_KEY or
GROQ_API_KEY. Groq additionally requires AGENT_CORE_GROQ_FREE_TIER=1, confirming
the key belongs to a free-plan account. This sends a real request and may incur
provider charges (OpenAI, Anthropic) or consume free-tier quota (Groq).
"""

import asyncio
import json
import os
import secrets
import tempfile
from datetime import UTC, datetime
from pathlib import Path

from agent_core import Limits, Policy, Registry, Runtime, Status, Store, Tool


async def main() -> None:
    if os.environ.get("AGENT_CORE_LIVE") != "1":
        raise SystemExit("Live testing disabled; explicit AGENT_CORE_LIVE=1 required.")
    provider = os.environ["AGENT_CORE_PROVIDER"]
    model_id = os.environ["AGENT_CORE_MODEL"]
    streaming = os.environ.get("AGENT_CORE_STREAMING", "0")
    if streaming not in {"0", "1"}:
        raise SystemExit("AGENT_CORE_STREAMING must be 0 or 1.")
    native_stream = streaming == "1"
    effects = []
    receipt = secrets.token_hex(16)

    def sum_integers(left: int, right: int) -> dict[str, int | str]:
        """Return the sum and a receipt that must be copied into the final answer."""
        effects.append((left, right))
        return {"sum": left + right, "receipt": receipt}

    if provider == "openai":
        from agent_core.providers.openai_chat import OpenAIChatModel

        key = os.environ["OPENAI_API_KEY"]
        model = OpenAIChatModel(model_id, key, streaming=native_stream)
    elif provider == "groq":
        if os.environ.get("AGENT_CORE_GROQ_FREE_TIER") != "1":
            raise SystemExit("Confirm a Groq free-plan account with AGENT_CORE_GROQ_FREE_TIER=1.")
        from agent_core.providers.groq import GroqModel

        key = os.environ["GROQ_API_KEY"]
        model = GroqModel(model_id, key, streaming=native_stream)
    elif provider == "anthropic":
        from agent_core.providers.anthropic import AnthropicModel

        key = os.environ["ANTHROPIC_API_KEY"]
        model = AnthropicModel(model_id, key, streaming=native_stream)
    else:
        raise SystemExit("Only openai, anthropic or groq is supported.")
    tool = Tool.from_callable(sum_integers)
    # Groq reasoning models count hidden reasoning against max_completion_tokens.
    output_tokens = 512 if provider == "groq" else 128
    with tempfile.TemporaryDirectory() as directory:
        store = Store(Path(directory) / "live.sqlite")
        try:
            runtime = Runtime(
                model,
                Registry((tool,)),
                store,
                Policy(allowed_tools=frozenset({"sum_integers"})),
                secrets=(key,),
                limits=Limits(turns=3, tools=1, seconds=60, output_tokens=output_tokens),
            )
            run = await runtime.run(
                "Call sum_integers once with left=17 and right=25. "
                "Return JSON with sum and the exact receipt from the tool observation.",
                output_schema={
                    "type": "object",
                    "properties": {"sum": {"type": "integer"}, "receipt": {"type": "string"}},
                    "required": ["sum", "receipt"],
                    "additionalProperties": False,
                },
            )
            assert run.status == Status.COMPLETED, run.reason
            assert effects == [(17, 25)], effects
            assert run.output == {"sum": 42, "receipt": receipt}, "Incorrect tool observation."
            assert run.usage.total is not None, "Live usage receipt is required."
            print(
                json.dumps(
                    {
                        "verified_at": datetime.now(UTC).isoformat(),
                        "api_profile": model.identity,
                        "native_streaming": native_stream,
                        "provider": provider,
                        "model": model_id,
                        "status": run.status,
                        "tool_count": run.tool_count,
                        "model_turns": run.turns,
                        "output_token_limit": output_tokens,
                        "observation_verified": True,
                        "usage": run.usage.model_dump(),
                    },
                    indent=2,
                )
            )
        finally:
            store.close()


if __name__ == "__main__":
    asyncio.run(main())
