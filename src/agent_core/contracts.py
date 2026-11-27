"""Serializable contracts. No execution authority is inferred from messages."""

from __future__ import annotations

import hashlib
import json
from enum import StrEnum
from typing import Any, Protocol
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator

Json = Any


def canonical(value: Json) -> str:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    )


def digest(value: Json) -> str:
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def new_id() -> str:
    return uuid4().hex


class Record(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Status(StrEnum):
    CREATED = "created"
    RUNNING = "running"
    WAITING = "waiting_approval"
    UNCERTAIN = "needs_reconciliation"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    BUDGET = "budget_exceeded"

    @property
    def terminal(self) -> bool:
        return self in {self.COMPLETED, self.FAILED, self.CANCELLED, self.BUDGET}


TRANSITIONS: dict[Status, set[Status]] = {
    Status.CREATED: {Status.RUNNING, Status.CANCELLED},
    Status.RUNNING: {
        Status.WAITING,
        Status.UNCERTAIN,
        Status.COMPLETED,
        Status.FAILED,
        Status.CANCELLED,
        Status.BUDGET,
    },
    Status.WAITING: {Status.RUNNING, Status.CANCELLED, Status.FAILED, Status.BUDGET},
    Status.UNCERTAIN: {Status.RUNNING},
}


class Effect(StrEnum):
    READ = "read"
    WRITE = "write"
    EXTERNAL = "external"


class Usage(Record):
    input_tokens: int | None = Field(default=None, ge=0)
    output_tokens: int | None = Field(default=None, ge=0)

    @property
    def total(self) -> int | None:
        if self.input_tokens is None or self.output_tokens is None:
            return None
        return self.input_tokens + self.output_tokens


class Call(Record):
    id: str = Field(min_length=1, max_length=128)
    name: str = Field(min_length=1, max_length=64)
    arguments: dict[str, Json]


class Response(Record):
    text: str = ""
    calls: tuple[Call, ...] = ()
    finish: str = "stop"
    usage: Usage = Usage()
    metadata: dict[str, Json] = Field(default_factory=dict)

    @model_validator(mode="after")
    def complete(self) -> Response:
        if self.finish not in {"stop", "tool_calls", "refusal"}:
            raise ValueError("incomplete or unsupported response")
        if self.finish == "tool_calls" and not self.calls:
            raise ValueError("tool response has no calls")
        if self.calls and self.finish != "tool_calls":
            raise ValueError("calls require tool_calls finish")
        if len({c.id for c in self.calls}) != len(self.calls):
            raise ValueError("duplicate call identity")
        canonical(self.model_dump(mode="json"))
        return self


class Message(Record):
    role: str
    content: str = ""
    calls: tuple[Call, ...] = ()
    call_id: str | None = None
    metadata: dict[str, Json] = Field(default_factory=dict)


class Limits(Record):
    turns: int = Field(default=16, ge=1, le=1000)
    tools: int = Field(default=32, ge=1, le=10000)
    seconds: float = Field(default=120, gt=0, le=86400)
    tokens: int | None = Field(default=None, ge=1)
    output_tokens: int = Field(default=1024, ge=1)
    context_bytes: int = Field(default=65536, ge=128)
    response_bytes: int = Field(default=1048576, ge=128)
    argument_bytes: int = Field(default=16384, ge=2)
    preview_bytes: int = Field(default=4096, ge=128)
    artifact_bytes: int = Field(default=1048576, ge=128)
    approval_seconds: float = Field(default=300, gt=0)


class Request(Record):
    run_id: str
    turn: int
    messages: tuple[Message, ...]
    tools: tuple[dict[str, Json], ...]
    max_output_tokens: int
    output_schema: dict[str, Json] | None = None


class Model(Protocol):
    identity: str

    async def complete(self, request: Request) -> Response: ...


class Run(Record):
    id: str
    session_id: str
    status: Status = Status.CREATED
    prompt: str
    instructions: str
    config_digest: str
    deadline: float
    turns: int = 0
    tool_count: int = 0
    usage: Usage = Usage(input_tokens=0, output_tokens=0)
    groups: tuple[tuple[Message, ...], ...] = ()
    pending: Response | None = None
    next_call: int = 0
    results: tuple[Message, ...] = ()
    output_schema: dict[str, Json] | None = None
    output: Json = None
    reason: str | None = None


class Operation(Record):
    id: str
    run_id: str
    call: Call
    status: str = "prepared"
    binding: str
    manifest: str
    effect: Effect
    expires_at: float | None = None
    approval: str | None = None
    actor: str | None = None
    result: str | None = None
    code: str | None = None
    duration: float | None = None


class Event(Record):
    sequence: int
    run_id: str
    kind: str
    timestamp: float
    operation_id: str | None = None
    data: dict[str, Json] = Field(default_factory=dict)


class CoreError(Exception):
    def __init__(self, code: str, *, retryable: bool = False):
        super().__init__(code)
        self.code = code
        self.retryable = retryable
