"""Deterministic offline model indexed by durable model turn."""

from collections.abc import Callable

from .contracts import CoreError, Request, Response


class ScriptedModel:
    def __init__(self, steps: tuple[Response | Callable[[Request], Response], ...]):
        self.steps = steps
        self.identity = "scripted-v1"
        self.requests: list[Request] = []

    async def complete(self, request: Request) -> Response:
        self.requests.append(request)
        try:
            step = self.steps[request.turn]
        except IndexError as exc:
            raise CoreError("script_exhausted") from exc
        return step(request) if callable(step) else step.model_copy(deep=True)
