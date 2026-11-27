"""Local host commands. Approval commands must be run by a trusted operator."""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from . import scenarios
from .contracts import CoreError, Run, Status
from .runtime import Runtime
from .store import Store


def _runtime(args: argparse.Namespace, store: Store) -> Runtime:
    if args.scenario == "research":
        return scenarios.research(store)
    if args.workspace is None:
        raise CoreError("workspace_required")
    factory = scenarios.workspace if args.scenario == "workspace" else scenarios.uncertain
    return factory(store, Path(args.workspace))


def _show(store: Store, run: Run) -> None:
    print(
        json.dumps(
            {
                "run": run.model_dump(mode="json"),
                "operations": [op.model_dump(mode="json") for op in store.operations(run.id)],
            },
            indent=2,
        )
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="agent-core", description="Local Agent Core host")
    parser.add_argument("--db", type=Path, default=Path("agent-core.sqlite"))
    parser.add_argument(
        "--scenario", choices=["research", "workspace", "uncertain"], default="research"
    )
    parser.add_argument("--workspace", type=Path)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("demo")
    for command in ["show", "resume", "cancel", "events", "stream"]:
        child = sub.add_parser(command)
        child.add_argument("run_id")
    approval = sub.add_parser("approve")
    approval.add_argument("run_id")
    approval.add_argument("operation_id")
    approval.add_argument("binding")
    approval.add_argument("--actor", required=True)
    approval.add_argument("--deny", action="store_true")
    reconciliation = sub.add_parser("reconcile")
    reconciliation.add_argument("run_id")
    reconciliation.add_argument("operation_id")
    reconciliation.add_argument("result_json")
    reconciliation.add_argument("--actor", required=True)
    artifact = sub.add_parser("artifact")
    artifact.add_argument("artifact_id")
    artifact.add_argument("--offset", type=int, default=0)
    artifact.add_argument("--limit", type=int, default=4096)
    args = parser.parse_args(argv)
    store = Store(args.db)
    try:
        if args.command == "show":
            _show(store, store.load(args.run_id))
        elif args.command == "events":
            cursor = 0
            while page := store.events(args.run_id, cursor):
                for event in page:
                    print(event.model_dump_json())
                    cursor = event.sequence
        elif args.command == "cancel":
            store.cancel(args.run_id)
            print(json.dumps({"cancel_requested": args.run_id}))
        elif args.command == "approve":
            store.decide(args.run_id, args.operation_id, args.binding, args.actor, not args.deny)
            print(json.dumps({"decision_recorded": args.operation_id}))
        elif args.command == "artifact":
            print(store.read_artifact(args.artifact_id, args.offset, args.limit))
        else:
            runtime = _runtime(args, store)
            if args.command == "reconcile":
                run = runtime.reconcile(
                    args.run_id, args.operation_id, json.loads(args.result_json), actor=args.actor
                )
            elif args.command == "demo":
                run = asyncio.run(runtime.run("Execute the selected local demonstration."))
            elif args.command == "stream":

                async def consume() -> Run:
                    async for event in runtime.stream(args.run_id):
                        print(event.model_dump_json(), flush=True)
                    return store.load(args.run_id)

                run = asyncio.run(consume())
            else:
                run = asyncio.run(runtime.resume(args.run_id))
            _show(store, run)
            if run.status in {Status.FAILED, Status.BUDGET, Status.CANCELLED}:
                return 1
        return 0
    except (CoreError, ValueError) as exc:
        print(json.dumps({"error": exc.code if isinstance(exc, CoreError) else "invalid_input"}))
        return 2
    finally:
        store.close()
