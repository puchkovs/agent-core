"""Bounded context projection preserving complete tool/result groups."""

from .contracts import CoreError, Limits, Message, Request, Run, canonical
from .policy import Decision, Policy
from .tools import Registry


def project(run: Run, registry: Registry, policy: Policy, limits: Limits) -> Request:
    tools = tuple(t.declaration for t in registry.all() if policy.decide(t) != Decision.DENY)
    pinned = (
        Message(role="system", content=run.instructions),
        Message(role="user", content=run.prompt),
    )
    groups = list(run.groups)
    while True:
        request = Request(
            run_id=run.id,
            turn=run.turns,
            messages=pinned + tuple(message for group in groups for message in group),
            tools=tools,
            max_output_tokens=limits.output_tokens,
            output_schema=run.output_schema,
        )
        if len(canonical(request.model_dump(mode="json")).encode()) <= limits.context_bytes:
            return request
        if not groups:
            raise CoreError("context_limit")
        groups.pop(0)
