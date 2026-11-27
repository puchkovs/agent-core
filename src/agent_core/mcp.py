"""Optional SDK-backed MCP tools; host policy owns all execution authority."""

from __future__ import annotations

import asyncio
import math
import re
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from functools import partial
from urllib.parse import urlsplit

import httpx
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

from .contracts import CoreError, Effect, Json, canonical, digest
from .tools import Registry, Tool, check_schema, validate


@dataclass(frozen=True)
class MCPConfig:
    namespace: str
    url: str
    headers: dict[str, str] = field(default_factory=dict, repr=False)
    timeout: float = 30
    max_tools: int = 128
    max_pages: int = 8
    result_bytes: int = 1048576
    allow_local_http: bool = False

    def __post_init__(self) -> None:
        url = urlsplit(self.url)
        local = self.allow_local_http and url.hostname in {"127.0.0.1", "::1", "localhost"}
        if (
            (url.scheme != "https" and not (url.scheme == "http" and local))
            or url.username
            or url.password
        ):
            raise ValueError("HTTPS endpoint or explicit loopback HTTP required")
        if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{0,15}", self.namespace):
            raise ValueError("invalid MCP namespace")
        if not math.isfinite(self.timeout) or self.timeout <= 0:
            raise ValueError("finite positive MCP timeout required")
        if (
            not 1 <= self.max_tools <= 1024
            or not 1 <= self.max_pages <= 128
            or self.result_bytes < 128
        ):
            raise ValueError("invalid MCP resource bounds")


class MCPTools:
    """Bridge an initialized session into the ordinary registry and Tool Engine.

    Discovery is explicit and atomic. Server instructions/annotations never enter
    host policy. Keep the session open until every registered invocation finishes.
    """

    def __init__(self, session: ClientSession, config: MCPConfig):
        self.session, self.config = session, config
        self.closed = False

    async def register(self, registry: Registry) -> tuple[str, ...]:
        if self.closed:
            raise CoreError("mcp_closed")
        pending: list[Tool] = []
        cursor = None
        seen: set[str] = set()
        try:
            async with asyncio.timeout(self.config.timeout):
                for _ in range(self.config.max_pages):
                    page = await self.session.list_tools(cursor=cursor)
                    for remote in page.tools:
                        if len(canonical(remote.model_dump(mode="json")).encode()) > 65536:
                            raise CoreError("mcp_manifest_limit")
                        name = self.config.namespace + "__" + remote.name
                        if name in seen or any(t.name == name for t in registry.all()):
                            raise CoreError("mcp_duplicate_tool")
                        seen.add(name)
                        if len(seen) > self.config.max_tools:
                            raise CoreError("mcp_tool_limit")
                        schema = dict(remote.inputSchema)
                        # No rebasing or remote references: Tool registration normalizes
                        # the accepted schema dialect using existing local-only checks.
                        schema.setdefault("$schema", "https://json-schema.org/draft/2020-12/schema")
                        output = remote.outputSchema
                        if output is not None:
                            check_schema(output)
                        pending.append(
                            Tool(
                                name=name,
                                description=remote.description or "",
                                function=partial(self._execute, remote.name, output),
                                input_schema=schema,
                                effect=Effect.EXTERNAL,
                                version=digest([self.config.url, remote.model_dump(mode="json")]),
                                permissions=frozenset({"mcp:" + name}),
                                timeout=self.config.timeout,
                            )
                        )
                    if page.nextCursor is None:
                        break
                    if page.nextCursor == cursor:
                        raise CoreError("mcp_pagination")
                    cursor = page.nextCursor
                else:
                    raise CoreError("mcp_page_limit")
        except CoreError:
            raise
        except Exception as exc:
            raise CoreError("mcp_discovery") from exc
        for tool in pending:
            registry.register(tool)
        return tuple(tool.name for tool in pending)

    async def _execute(
        self, name: str, output: dict[str, Json] | None, /, **arguments: Json
    ) -> Json:
        if self.closed:
            raise CoreError("mcp_closed")
        try:
            async with asyncio.timeout(self.config.timeout):
                result = await self.session.call_tool(name, arguments)
            if result.isError:
                raise CoreError("mcp_tool_error")
            if output is not None:
                validate(output, result.structuredContent, "invalid_output")
            value = result.model_dump(mode="json", exclude_none=True)
            if len(canonical(value).encode()) > self.config.result_bytes:
                raise CoreError("output_limit")
            return value
        except CoreError:
            raise
        except Exception as exc:
            raise CoreError("mcp_transport") from exc


@asynccontextmanager
async def connect(config: MCPConfig) -> AsyncIterator[MCPTools]:
    """Open a host-selected HTTP server; never launch a subprocess or auto-retry calls."""
    async with httpx.AsyncClient(
        headers=config.headers,
        timeout=config.timeout,
        follow_redirects=False,
        trust_env=False,
    ) as http:
        async with streamable_http_client(config.url, http_client=http) as (read, write, _):
            async with ClientSession(read, write) as session:
                async with asyncio.timeout(config.timeout):
                    initialized = await session.initialize()
                if initialized.protocolVersion != "2025-11-25":
                    raise CoreError("mcp_protocol")
                if initialized.capabilities.tools is None:
                    raise CoreError("mcp_tools_unavailable")
                bridge = MCPTools(session, config)
                try:
                    yield bridge
                finally:
                    bridge.closed = True
