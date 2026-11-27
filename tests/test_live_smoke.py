import importlib.util
import json
from pathlib import Path

import pytest

from agent_core import Call, Response, Usage


def load_smoke():
    path = Path(__file__).parents[1] / "evaluation/live_smoke.py"
    spec = importlib.util.spec_from_file_location("live_smoke_fixture", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("correct_receipt", [True, False])
@pytest.mark.parametrize("provider", ["openai", "anthropic"])
@pytest.mark.parametrize("streaming", ["0", "1"])
async def test_live_procedure_uses_actual_observation_without_network(
    monkeypatch, capsys, provider, streaming, correct_receipt
):
    import agent_core.providers.anthropic as anthropic
    import agent_core.providers.openai_chat as openai

    class Model:
        identity = "fixture-profile"

        async def complete(self, request):
            if request.turn == 0:
                return Response(
                    calls=(
                        Call(id="sum", name="sum_integers", arguments={"left": 17, "right": 25}),
                    ),
                    finish="tool_calls",
                    usage=Usage(input_tokens=1, output_tokens=1),
                )
            observation = json.loads(request.messages[-1].content)
            assert observation["sum"] == 42
            assert len(observation["receipt"]) == 32
            if not correct_receipt:
                observation["receipt"] = "incorrect-receipt"
            return Response(
                text=json.dumps(observation), usage=Usage(input_tokens=1, output_tokens=1)
            )

    def factory(model, key, *, streaming):
        assert model == "fixture-model" and key == "fixture-key"
        return Model()

    monkeypatch.setattr(openai, "OpenAIChatModel", factory)
    monkeypatch.setattr(anthropic, "AnthropicModel", factory)
    for name, value in {
        "AGENT_CORE_LIVE": "1",
        "AGENT_CORE_PROVIDER": provider,
        "AGENT_CORE_MODEL": "fixture-model",
        "AGENT_CORE_STREAMING": streaming,
        "OPENAI_API_KEY": "fixture-key",
        "ANTHROPIC_API_KEY": "fixture-key",
    }.items():
        monkeypatch.setenv(name, value)
    if not correct_receipt:
        with pytest.raises(AssertionError, match="Incorrect tool observation"):
            await load_smoke().main()
        assert capsys.readouterr().out == ""
        return
    await load_smoke().main()
    evidence = json.loads(capsys.readouterr().out)
    assert evidence["observation_verified"] is True
    assert evidence["model_turns"] == 2 and evidence["tool_count"] == 1
    assert evidence["native_streaming"] == (streaming == "1")
    assert "fixture-key" not in json.dumps(evidence)


async def test_live_procedure_requires_explicit_opt_in(monkeypatch):
    monkeypatch.delenv("AGENT_CORE_LIVE", raising=False)
    with pytest.raises(SystemExit, match="Live testing disabled"):
        await load_smoke().main()
