"""Reproducible local overhead measurements; no language-model quality claims."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import importlib.metadata
import json
import math
import platform
import statistics
import subprocess
import tempfile
import time
from pathlib import Path

from agent_core import (
    Call,
    Policy,
    Registry,
    Response,
    Runtime,
    ScriptedModel,
    Status,
    Store,
    Tool,
    Usage,
)


async def sample(root: Path, index: int) -> dict[str, float | int]:
    def add(left: int, right: int) -> int:
        return left + right

    tool = Tool.from_callable(add)
    model = ScriptedModel(
        (
            Response(
                calls=(Call(id="sum", name="add", arguments={"left": index, "right": 7}),),
                finish="tool_calls",
                usage=Usage(input_tokens=0, output_tokens=0),
            ),
            Response(text="done", usage=Usage(input_tokens=0, output_tokens=0)),
        )
    )
    started = time.perf_counter_ns()
    store = Store(root / f"sample-{index}.sqlite")
    runtime = Runtime(model, Registry((tool,)), store, Policy(allowed_tools=frozenset({"add"})))
    try:
        run = await runtime.run("add two integers")
        assert run.status == Status.COMPLETED
        operation = store.operations(run.id)[0]
        assert json.loads(operation.result) == index + 7
        duration = (time.perf_counter_ns() - started) / 1e6
        return {
            "index": index,
            "end_to_end_ms": duration,
            "tool_ms": (operation.duration or 0) * 1000,
            "events": len(store.events(run.id)),
        }
    finally:
        store.close()


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--samples", type=int, default=100)
    args = parser.parse_args()
    if not 10 <= args.samples <= 10000:
        parser.error("samples must be between 10 and 10000")
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        for index in range(5):
            await sample(root, -index - 1)
        rows = [await sample(root, index) for index in range(args.samples)]
    times = sorted(float(row["end_to_end_ms"]) for row in rows)
    source = Path(__file__).parents[1]
    files = sorted((source / "src").rglob("*.py"))
    fingerprint = hashlib.sha256()
    for file in files:
        fingerprint.update(str(file.relative_to(source)).encode())
        fingerprint.update(file.read_bytes())
    commit = await asyncio.to_thread(
        subprocess.check_output, ["git", "rev-parse", "HEAD"], text=True
    )
    status = await asyncio.to_thread(
        subprocess.check_output, ["git", "status", "--porcelain"], text=True
    )
    report = {
        "schema": 1,
        "kind": "offline_runtime_overhead",
        "samples": len(rows),
        "warmup": 5,
        "python": platform.python_version(),
        "platform": platform.platform(),
        "sqlite": __import__("sqlite3").sqlite_version,
        "commit": commit.strip(),
        "dirty": bool(status.strip()),
        "source_sha256": fingerprint.hexdigest(),
        "dependencies": {
            name: importlib.metadata.version(name) for name in ["pydantic", "jsonschema", "httpx"]
        },
        "configuration": {
            "tool_calls": 1,
            "model_calls": 2,
            "journal": "WAL/FULL",
            "execution": "sequential",
            "new_database_per_sample": True,
        },
        "summary_ms": {
            "median": statistics.median(times),
            "p95_nearest_rank": times[math.ceil(0.95 * len(times)) - 1],
            "min": min(times),
            "max": max(times),
        },
        "limitations": [
            "Synthetic scripted model; not intelligence or provider latency.",
            "Includes new SQLite database initialization and filesystem synchronization.",
            "Shared container, uncontrolled scheduling/cache, no comparative performance claim.",
        ],
        "raw": rows,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report["summary_ms"], indent=2))


if __name__ == "__main__":
    asyncio.run(main())
