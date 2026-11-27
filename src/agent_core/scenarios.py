"""Original offline scenarios with observed-result assertions, not intelligence scores."""

from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from pathlib import Path

from .contracts import Call, Effect, Json, Request, Response, Usage
from .models import ScriptedModel
from .policy import Policy
from .runtime import Runtime
from .store import Store
from .tools import Registry, Tool

# Original synthetic local files are shipped with the package for offline use.
DATA_ROOT = Path(__file__).with_name("data")
DOCUMENT_IDS = ("pilot", "cost", "caution")


def _read_document(document: str) -> str:
    if document not in DOCUMENT_IDS:
        raise ValueError("unknown local document")
    return (DATA_ROOT / (document + ".md")).read_text()


def proposal(*items: tuple[str, dict[str, Json]]) -> Response:
    return Response(
        calls=tuple(
            Call(id=str(i), name=name, arguments=args) for i, (name, args) in enumerate(items)
        ),
        finish="tool_calls",
        usage=Usage(input_tokens=0, output_tokens=0),
    )


def final(text: str) -> Response:
    return Response(text=text, usage=Usage(input_tokens=0, output_tokens=0))


def research(store: Store) -> Runtime:
    def search(query: str) -> list[str]:
        """Search local planning evidence by keyword; return document identifiers."""
        return sorted(
            k for k in DOCUMENT_IDS if query.casefold() in (k + _read_document(k)).casefold()
        )

    def read(document: str) -> dict[str, str]:
        """Read a document from the explicitly prepared local collection."""
        return {"id": document, "text": _read_document(document)}

    def calculate(baseline: float, trial: float, price: float, days: int) -> dict[str, float]:
        """Compute savings from the supplied measurements and synthetic assumptions."""
        if baseline <= 0 or not 0 <= trial <= baseline or price < 0 or days < 0:
            raise ValueError("invalid planning inputs")
        return {
            "daily_kwh": baseline - trial,
            "monthly_credits": round((baseline - trial) * price * days, 2),
        }

    def choose_reads(request: Request) -> Response:
        observed = json.loads(request.messages[-1].content)
        if "cost" not in observed:
            return final("No energy assumptions found")
        return proposal(*(("read", {"document": key}) for key in ("pilot", "cost", "caution")))

    def choose_calculation(request: Request) -> Response:
        observations = [json.loads(m.content) for m in request.messages if m.role == "tool"]
        documents = {o["id"]: o["text"] for o in observations if isinstance(o, dict) and "id" in o}
        assert "used 18" in documents["pilot"]
        assert "0.20" in documents["cost"]
        return proposal(("calculate", {"baseline": 18.0, "trial": 12.0, "price": 0.20, "days": 20}))

    def synthesize(request: Request) -> Response:
        result = json.loads(request.messages[-1].content)
        return final(
            json.dumps(
                {
                    "daily_savings_kwh": result["daily_kwh"],
                    "monthly_savings_credits": result["monthly_credits"],
                    "sources": ["pilot", "cost", "caution"],
                    "limitation": (
                        "Local trial and synthetic price; no forecast for other buildings."
                    ),
                }
            )
        )

    tools = tuple(Tool.from_callable(f) for f in (search, read, calculate))
    model = ScriptedModel(
        (proposal(("search", {"query": "energy"})), choose_reads, choose_calculation, synthesize)
    )
    return Runtime(
        model, Registry(tools), store, Policy(allowed_tools=frozenset(t.name for t in tools))
    )


def workspace(store: Store, root: Path) -> Runtime:
    root = root.resolve()
    root.mkdir(parents=True, exist_ok=True)

    def check(arguments: dict[str, Json]) -> None:
        if not re.fullmatch(r"[A-Za-z0-9_-]+\.md", arguments["name"]):
            raise ValueError("only a Markdown basename is allowed")
        target = root / arguments["name"]
        if target.is_symlink():
            raise ValueError("symlink target is forbidden")

    def write(name: str, text: str, expected_sha256: str) -> dict[str, str]:
        """Write a Markdown file if its current digest matches the approved precondition."""
        check({"name": name})
        target = root / name
        previous = target.read_bytes() if target.exists() else b""
        if hashlib.sha256(previous).hexdigest() != expected_sha256:
            raise ValueError("file changed since preparation")
        temporary: str | None = None
        try:
            with tempfile.NamedTemporaryFile(dir=root, delete=False) as handle:
                temporary = handle.name
                handle.write(text.encode())
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, target)
            temporary = None
            return {"name": name, "sha256": hashlib.sha256(text.encode()).hexdigest()}
        finally:
            if temporary is not None:
                Path(temporary).unlink(missing_ok=True)

    tool = Tool.from_callable(
        write, effect=Effect.WRITE, permissions=frozenset({"notes:write"}), semantic=check
    )
    empty_digest = hashlib.sha256(b"").hexdigest()
    model = ScriptedModel(
        (
            proposal(
                (
                    "write",
                    {
                        "name": "plan.md",
                        "text": "# Plan\nMeasure before expanding.\n",
                        "expected_sha256": empty_digest,
                    },
                )
            ),
            final("The approved note was saved."),
        )
    )
    return Runtime(
        model,
        Registry((tool,)),
        store,
        Policy(
            allowed_tools=frozenset({"write"}),
            permissions=frozenset({"notes:write"}),
            scope=str(root),
        ),
    )


def uncertain(store: Store, root: Path) -> Runtime:
    root = root.resolve()
    root.mkdir(parents=True, exist_ok=True)
    receipt = root / "service-receipts.jsonl"

    def send(message: str) -> str:
        """Simulate an external service accepting a request before losing its response."""
        with receipt.open("a") as handle:
            handle.write(json.dumps({"receipt": "simulated-1", "message": message}) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        raise ConnectionError("response lost after remote acceptance")

    tool = Tool.from_callable(send, effect=Effect.EXTERNAL)
    model = ScriptedModel(
        (
            proposal(("send", {"message": "reserve one trial slot"})),
            final("Receipt confirmed by host reconciliation."),
        )
    )
    return Runtime(
        model, Registry((tool,)), store, Policy(allowed_tools=frozenset({"send"}), scope=str(root))
    )
