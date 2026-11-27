"""Sequential orchestration with durable admission and conservative recovery."""

from __future__ import annotations

import asyncio
import contextlib
import inspect
import json
import time
from collections.abc import AsyncIterator, Awaitable
from typing import Any, TypeVar

from .context import project
from .contracts import (
    Call,
    CoreError,
    Effect,
    Event,
    Json,
    Limits,
    Message,
    Model,
    Operation,
    Response,
    Run,
    Status,
    Usage,
    canonical,
    digest,
    new_id,
)
from .policy import Decision, Policy
from .store import Store
from .tools import Registry, Tool, check_schema, validate

T = TypeVar("T")


class Runtime:
    def __init__(
        self,
        model: Model,
        registry: Registry,
        store: Store,
        policy: Policy | None = None,
        limits: Limits | None = None,
        *,
        instructions: str = "Use tools to answer the user's task.",
        secrets: tuple[str, ...] = (),
    ):
        self.model = model
        self.registry = registry
        self.store = store
        self.policy = policy or Policy()
        self.limits = limits or Limits()
        self.instructions = instructions
        self.secrets = tuple(s for s in secrets if s)

    @property
    def config_digest(self) -> str:
        return digest(
            {
                "model": self.model.identity,
                "tools": [t.manifest for t in self.registry.all()],
                "policy": self.policy.identity,
                "limits": self.limits.model_dump(),
                "instructions": self.instructions,
            }
        )

    def create(
        self,
        prompt: str,
        *,
        session_id: str | None = None,
        output_schema: dict[str, Json] | None = None,
    ) -> str:
        if len(prompt.encode()) > self.limits.context_bytes:
            raise CoreError("context_limit")
        if output_schema is not None:
            check_schema(output_schema)
        run = Run(
            id=new_id(),
            session_id=session_id or new_id(),
            prompt=prompt,
            instructions=self.instructions,
            config_digest=self.config_digest,
            deadline=time.time() + self.limits.seconds,
            output_schema=output_schema,
        )
        self.store.create(run)
        return run.id

    async def run(self, prompt: str, **kwargs: Any) -> Run:
        return await self.resume(self.create(prompt, **kwargs))

    def cancel(self, run_id: str) -> None:
        self.store.cancel(run_id)

    def approve(
        self,
        run_id: str,
        operation_id: str,
        binding: str,
        *,
        actor: str,
        allow: bool = True,
    ) -> None:
        self.store.decide(run_id, operation_id, binding, actor, allow)

    def _finish(self, run: Run, status: Status, reason: str, output: Json = None) -> Run:
        updated = run.model_copy(update={"status": status, "reason": reason, "output": output})
        self.store.save(updated, "run." + status.value, data={"reason": reason})
        return updated

    def _redact(self, value: str) -> str:
        for secret in self.secrets:
            value = value.replace(secret, "[REDACTED]")
        return value

    async def _bounded(self, work: Awaitable[T], run: Run, wait_seconds: float) -> T:
        task = asyncio.ensure_future(work)
        started = time.monotonic()
        try:
            while True:
                if self.store.cancelled(run.id):
                    raise CoreError("cancelled")
                remaining = min(
                    wait_seconds - (time.monotonic() - started), run.deadline - time.time()
                )
                if remaining <= 0:
                    raise CoreError("deadline")
                done, _ = await asyncio.wait({task}, timeout=min(remaining, 0.01))
                if done:
                    return task.result()
        finally:
            if not task.done():
                task.cancel()
                # Do not await an uncooperative coroutine indefinitely. Trusted tools
                # must honor cancellation; threads and external effects cannot be killed.
                task.add_done_callback(self._consume)
                await asyncio.sleep(0)

    @staticmethod
    def _consume(task: asyncio.Future[Any]) -> None:
        with contextlib.suppress(BaseException):
            task.result()

    def _binding(self, run: Run, op_id: str, call: Call, tool: Tool) -> str:
        return digest(
            {
                "run": run.id,
                "operation": op_id,
                "call": call.model_dump(mode="json"),
                "tool": tool.manifest,
                "policy": self.policy.identity,
                "constraints": run.config_digest,
            }
        )

    def _outcome(self, run: Run, operation: Operation, text: str, code: str | None) -> Run:
        message = Message(role="tool", content=text, call_id=operation.call.id)
        updated = run.model_copy(
            update={
                "results": run.results + (message,),
                "next_call": run.next_call + 1,
            }
        )
        operation = operation.model_copy(
            update={"status": "completed", "result": text, "code": code}
        )
        self.store.save(updated, "tool.completed", operation, {"code": code})
        return updated

    def _preview(self, result: Json) -> str:
        text = self._redact(canonical(result))
        raw = text.encode()
        if len(raw) > self.limits.artifact_bytes:
            raise CoreError("output_limit")
        if len(raw) <= self.limits.preview_bytes:
            return text
        key = self.store.artifact(text)
        return canonical(
            {
                "truncated": True,
                "artifact": key,
                "bytes": len(raw),
                "preview": raw[: self.limits.preview_bytes // 2].decode(errors="ignore"),
            }
        )

    async def _invoke(self, tool: Tool, call: Call) -> Json:
        args = json.loads(canonical(call.arguments))
        if inspect.iscoroutinefunction(tool.function):
            return await tool.function(**args)
        result = await asyncio.to_thread(tool.function, **args)
        if inspect.isawaitable(result):
            return await result
        return result

    async def _call(self, run: Run, call: Call) -> Run:
        op_id = digest([run.id, run.turns, run.next_call])
        existing = self.store.operation(op_id)
        try:
            tool = self.registry.get(call.name)
            if len(canonical(call.arguments).encode()) > self.limits.argument_bytes:
                raise CoreError("invalid_arguments")
            tool.validate(call.arguments)
        except CoreError as exc:
            # Invalid calls have observations but never enter dispatch.
            rejected = Operation(
                id=op_id,
                run_id=run.id,
                call=call,
                binding="",
                manifest="",
                effect=Effect.READ,
            )
            return self._outcome(run, rejected, canonical({"error": exc.code}), exc.code)
        binding = self._binding(run, op_id, call, tool)
        operation = existing or Operation(
            id=op_id,
            run_id=run.id,
            call=call,
            binding=binding,
            manifest=tool.manifest,
            effect=tool.effect,
        )
        if operation.binding != binding:
            return self._finish(run, Status.FAILED, "binding_changed")
        decision = self.policy.decide(tool)
        if decision == Decision.DENY:
            return self._finish(run, Status.FAILED, "policy_denied")
        if decision == Decision.APPROVAL:
            if operation.approval is None:
                if operation.expires_at is None:
                    operation = operation.model_copy(
                        update={
                            "expires_at": time.time() + self.limits.approval_seconds,
                        }
                    )
                paused = run.model_copy(update={"status": Status.WAITING})
                self.store.save(paused, "approval.requested", operation, {"binding": binding})
                return paused
            if operation.approval != "allow":
                return self._finish(run, Status.FAILED, "approval_denied")
            if operation.expires_at is None or time.time() >= operation.expires_at:
                return self._finish(run, Status.FAILED, "approval_expired")
        if run.tool_count >= self.limits.tools:
            return self._finish(run, Status.BUDGET, "tool_limit")
        if self.store.cancelled(run.id):
            return self._finish(run, Status.CANCELLED, "cancelled")
        if time.time() >= run.deadline:
            return self._finish(run, Status.BUDGET, "deadline")
        run = run.model_copy(update={"tool_count": run.tool_count + 1})
        operation = operation.model_copy(update={"status": "dispatched"})
        try:
            self.store.save(run, "tool.dispatched", operation)
        except CoreError as exc:
            if exc.code == "cancelled":
                return self._finish(self.store.load(run.id), Status.CANCELLED, "cancelled")
            raise
        started = time.monotonic()
        code: str | None = None
        try:
            result = await self._bounded(self._invoke(tool, call), run, tool.timeout)
        except BaseException as exc:
            if isinstance(exc, (KeyboardInterrupt, SystemExit)):
                raise
            code = exc.code if isinstance(exc, CoreError) else "tool_error"
            if isinstance(exc, asyncio.CancelledError):
                code = "cancelled"
            operation = operation.model_copy(update={"duration": time.monotonic() - started})
            if tool.effect != Effect.READ:
                uncertain = run.model_copy(
                    update={"status": Status.UNCERTAIN, "reason": "uncertain"}
                )
                self.store.save(
                    uncertain,
                    "tool.uncertain",
                    operation.model_copy(update={"status": "uncertain", "code": code}),
                )
                return uncertain
            if code == "cancelled":
                self._outcome(run, operation, canonical({"error": code}), code)
                return self._finish(self.store.load(run.id), Status.CANCELLED, code)
            if code == "deadline":
                self._outcome(run, operation, canonical({"error": code}), code)
                return self._finish(self.store.load(run.id), Status.BUDGET, code)
            return self._outcome(run, operation, canonical({"error": "tool_error"}), "tool_error")
        operation = operation.model_copy(update={"duration": time.monotonic() - started})
        try:
            if tool.output_schema is not None:
                validate(tool.output_schema, result, "invalid_output")
            text = self._preview(result)
        except (CoreError, TypeError, ValueError, RecursionError) as exc:
            code = exc.code if isinstance(exc, CoreError) else "invalid_output"
            text = canonical({"error": code})
        return self._outcome(run, operation, text, code)

    async def resume(self, run_id: str) -> Run:
        with self.store.driver(run_id):
            run = self.store.load(run_id)
            if run.status.terminal or run.status == Status.UNCERTAIN:
                return run
            # First discover unfinished I/O, even if configuration or cancellation changed.
            for operation in self.store.operations(run_id):
                if operation.status == "dispatched":
                    if run.status != Status.RUNNING:
                        raise CoreError("corrupt_checkpoint")
                    updated = run.model_copy(
                        update={"status": Status.UNCERTAIN, "reason": "uncertain"}
                    )
                    self.store.save(
                        updated,
                        "tool.uncertain",
                        operation.model_copy(
                            update={
                                "status": "uncertain",
                                "code": "interrupted",
                            }
                        ),
                    )
                    return updated
            if run.config_digest != self.config_digest:
                if run.status == Status.CREATED:
                    run = run.model_copy(update={"status": Status.RUNNING})
                    self.store.save(run, "run.running")
                return self._finish(run, Status.FAILED, "binding_changed")
            if self.store.cancelled(run_id):
                return self._finish(run, Status.CANCELLED, "cancelled")
            if run.status == Status.WAITING:
                pending = [op for op in self.store.operations(run_id) if op.status == "prepared"]
                if pending and pending[-1].approval is None:
                    if time.time() < min(pending[-1].expires_at or 0, run.deadline):
                        return run
                    run = run.model_copy(update={"status": Status.RUNNING})
                    self.store.save(run, "run.running")
                    return self._finish(run, Status.BUDGET, "approval_expired")
            run = run.model_copy(update={"status": Status.RUNNING, "reason": None})
            self.store.save(run, "run.running")
            while True:
                if self.store.cancelled(run_id):
                    return self._finish(run, Status.CANCELLED, "cancelled")
                if time.time() >= run.deadline:
                    return self._finish(run, Status.BUDGET, "deadline")
                if run.pending is not None:
                    response = run.pending
                    if self.limits.tokens is not None and (
                        run.usage.total is None or run.usage.total > self.limits.tokens
                    ):
                        return self._finish(
                            run,
                            Status.BUDGET,
                            "unknown_usage" if run.usage.total is None else "token_limit",
                        )
                    if response.finish == "refusal":
                        return self._finish(run, Status.FAILED, "refusal")
                    if not response.calls:
                        return self._final_output(run, response)
                    while run.next_call < len(run.pending.calls):
                        run = await self._call(run, run.pending.calls[run.next_call])
                        if run.status != Status.RUNNING:
                            return run
                    assistant = Message(
                        role="assistant",
                        content=response.text,
                        calls=response.calls,
                        metadata=response.metadata,
                    )
                    run = run.model_copy(
                        update={
                            "groups": run.groups + ((assistant,) + run.results,),
                            "pending": None,
                            "results": (),
                            "next_call": 0,
                        }
                    )
                    self.store.save(run, "context.checkpoint")
                    continue
                if run.turns >= self.limits.turns:
                    return self._finish(run, Status.BUDGET, "turn_limit")
                if self.limits.tokens is not None:
                    if run.usage.total is None:
                        return self._finish(run, Status.BUDGET, "unknown_usage")
                    if run.usage.total >= self.limits.tokens:
                        return self._finish(run, Status.BUDGET, "token_limit")
                try:
                    request = project(run, self.registry, self.policy, self.limits)
                    if self.limits.tokens is not None:
                        request = request.model_copy(
                            update={
                                "max_output_tokens": min(
                                    request.max_output_tokens,
                                    self.limits.tokens - (run.usage.total or 0),
                                )
                            }
                        )
                    self.store.save(run, "model.started", data={"turn": run.turns})
                    response = await self._bounded(
                        self.model.complete(request), run, self.limits.seconds
                    )
                    response = Response.model_validate_json(response.model_dump_json())
                    if len(response.model_dump_json().encode()) > self.limits.response_bytes:
                        raise CoreError("provider_response")
                except asyncio.CancelledError:
                    return self._finish(run, Status.CANCELLED, "cancelled")
                except Exception as exc:
                    code = exc.code if isinstance(exc, CoreError) else "provider_response"
                    status = (
                        Status.CANCELLED
                        if code == "cancelled"
                        else (
                            Status.BUDGET
                            if code in {"deadline", "context_limit"}
                            else Status.FAILED
                        )
                    )
                    return self._finish(run, status, code)

                def add(a: int | None, b: int | None) -> int | None:
                    return None if a is None or b is None else a + b

                usage = Usage(
                    input_tokens=add(run.usage.input_tokens, response.usage.input_tokens),
                    output_tokens=add(run.usage.output_tokens, response.usage.output_tokens),
                )
                run = run.model_copy(
                    update={
                        "turns": run.turns + 1,
                        "usage": usage,
                        "pending": response,
                    }
                )
                # Commit the complete response and usage together, including final answers.
                self.store.save(run, "model.completed", data={"usage": response.usage.model_dump()})

    def _final_output(self, run: Run, response: Response) -> Run:
        try:
            output: Json = response.text
            if run.output_schema is not None:
                output = json.loads(response.text)
                validate(run.output_schema, output, "invalid_output")
            output = json.loads(self._redact(canonical(output)))
        except (CoreError, ValueError, TypeError):
            return self._finish(run, Status.FAILED, "invalid_output")
        return self._finish(run, Status.COMPLETED, "model_final", output)

    def reconcile(self, run_id: str, operation_id: str, result: Json, *, actor: str) -> Run:
        if not actor.strip():
            raise CoreError("invalid_actor")
        with self.store.driver(run_id):
            run = self.store.load(run_id)
            operation = self.store.operation(operation_id)
            if (
                run.status != Status.UNCERTAIN
                or operation is None
                or operation.run_id != run_id
                or operation.status != "uncertain"
            ):
                raise CoreError("invalid_reconciliation")
            # The host confirms the actual outcome; this API cannot retry I/O.
            text = self._preview(result)
            run = run.model_copy(update={"status": Status.RUNNING, "reason": None})
            operation = operation.model_copy(update={"actor": actor})
            return self._outcome(run, operation, text, None)

    async def stream(self, run_id: str, *, after: int = 0) -> AsyncIterator[Event]:
        task = asyncio.create_task(self.resume(run_id))
        cursor = after
        try:
            while True:
                events = self.store.events(run_id, cursor)
                for event in events:
                    cursor = event.sequence
                    yield event
                if not events and task.done():
                    await task
                    break
                if not events:
                    await asyncio.sleep(0.01)
        finally:
            if not task.done():
                self.cancel(run_id)
                await task
