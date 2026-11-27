import json

import pytest

from agent_core import Status
from agent_core.cli import main
from agent_core.scenarios import research, uncertain, workspace


async def test_research_scenario_oracle(store):
    result = await research(store).run("energy")
    assert result.status == Status.COMPLETED
    output = json.loads(result.output)
    assert output["daily_savings_kwh"] == 6 and output["monthly_savings_credits"] == 24
    assert output["sources"] == ["pilot", "cost", "caution"]
    assert [op.call.name for op in store.operations(result.id)] == [
        "search",
        "read",
        "read",
        "read",
        "calculate",
    ]


async def test_workspace_restart_precondition_and_escape(store, tmp_path):
    runtime = workspace(store, tmp_path / "notes")
    paused = await runtime.run("create")
    op = store.operations(paused.id)[0]
    for name in ["../outside.md", "/outside.md", "nested/file.md"]:
        with pytest.raises(Exception, match="semantic_rejection"):
            runtime.registry.get("write").validate(
                {"name": name, "text": "bad", "expected_sha256": "x"}
            )
    runtime.approve(paused.id, op.id, op.binding, actor="tester")
    result = await workspace(store, tmp_path / "notes").resume(paused.id)
    assert result.status == Status.COMPLETED
    assert (tmp_path / "notes" / "plan.md").exists()
    paused = await workspace(store, tmp_path / "notes").run("repeat")
    op = store.operations(paused.id)[0]
    runtime.approve(paused.id, op.id, op.binding, actor="tester")
    assert (await runtime.resume(paused.id)).status == Status.UNCERTAIN


async def test_simulated_external_scenario(store, tmp_path):
    runtime = uncertain(store, tmp_path / "service")
    run = await runtime.run("reserve")
    op = store.operations(run.id)[0]
    runtime.approve(run.id, op.id, op.binding, actor="tester")
    run = await runtime.resume(run.id)
    assert run.status == Status.UNCERTAIN
    assert (await runtime.resume(run.id)).status == Status.UNCERTAIN
    receipts = (tmp_path / "service" / "service-receipts.jsonl").read_text().splitlines()
    assert len(receipts) == 1
    runtime.reconcile(run.id, op.id, json.loads(receipts[0]), actor="tester")
    assert (await runtime.resume(run.id)).status == Status.COMPLETED


def test_cli_research_and_errors(tmp_path, capsys):
    base = ["--db", str(tmp_path / "cli.sqlite")]
    assert main(base + ["demo"]) == 0
    result = json.loads(capsys.readouterr().out)
    run_id = result["run"]["id"]
    for command in ["show", "resume", "stream"]:
        assert main(base + [command, run_id]) == 0
        assert '"completed"' in capsys.readouterr().out
    assert main(base + ["events", run_id]) == 0
    assert "run.completed" in capsys.readouterr().out
    assert main(base + ["cancel", run_id]) == 0
    capsys.readouterr()
    assert main(base + ["show", "unknown"]) == 2
    assert "unknown_run" in capsys.readouterr().out
    assert main(base + ["--scenario", "workspace", "demo"]) == 2
    assert "workspace_required" in capsys.readouterr().out


def test_cli_approval_and_continuation(tmp_path, capsys):
    base = [
        "--db",
        str(tmp_path / "cli.sqlite"),
        "--scenario",
        "workspace",
        "--workspace",
        str(tmp_path / "notes"),
    ]
    assert main(base + ["demo"]) == 0
    data = json.loads(capsys.readouterr().out)
    run_id = data["run"]["id"]
    op = data["operations"][0]
    assert main(base + ["approve", run_id, op["id"], op["binding"], "--actor", "tester"]) == 0
    capsys.readouterr()
    assert main(base + ["resume", run_id]) == 0
    assert "completed" in capsys.readouterr().out
    assert (tmp_path / "notes" / "plan.md").read_text().startswith("# Plan")
