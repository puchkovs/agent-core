from contextlib import asynccontextmanager

import pytest
from mcp import types
from mcp.server import Server
from mcp.shared.memory import create_connected_server_and_client_session

from agent_core import Call, CoreError, Policy, Registry, Response, Runtime, ScriptedModel, Status
from agent_core.mcp import MCPConfig, MCPTools


@asynccontextmanager
async def server_session(*, failure=False):
    server = Server("agent-core-local-fixture")
    effects = []

    @server.list_tools()
    async def list_tools():
        return [
            types.Tool(
                name="write",
                description="Record an integer",
                inputSchema={
                    "type": "object",
                    "properties": {"value": {"type": "integer"}},
                    "required": ["value"],
                    "additionalProperties": False,
                },
            )
        ]

    @server.call_tool()
    async def call_tool(name, arguments):
        effects.append(arguments["value"])
        if failure:
            raise ValueError("private server failure")
        return [types.TextContent(type="text", text=str(arguments["value"]))]

    async with create_connected_server_and_client_session(server) as session:
        yield session, effects


async def test_real_sdk_local_server_approval_resume_and_no_replay(store):
    async with server_session() as (session, effects):
        registry = Registry()
        bridge = MCPTools(session, MCPConfig("local", "https://fixture.example/mcp"))
        assert await bridge.register(registry) == ("local__write",)
        model = ScriptedModel(
            (
                Response(
                    calls=(Call(id="one", name="local__write", arguments={"value": 3}),),
                    finish="tool_calls",
                ),
                Response(text="done"),
            )
        )
        runtime = Runtime(
            model,
            registry,
            store,
            Policy(
                allowed_tools=frozenset({"local__write"}),
                permissions=frozenset({"mcp:local__write"}),
            ),
        )
        run = await runtime.run("write")
        assert run.status == Status.WAITING and effects == []
        operation = store.operations(run.id)[0]
        runtime.approve(run.id, operation.id, operation.binding, actor="host")
        run = await runtime.resume(run.id)
        assert run.status == Status.COMPLETED and effects == [3]
        await runtime.resume(run.id)
        assert effects == [3]
        bridge.closed = True
        with pytest.raises(CoreError, match="mcp_closed"):
            await bridge.register(Registry())


@pytest.mark.parametrize("mode", ["denied", "invalid", "failure"])
async def test_mcp_runtime_security_and_uncertain_failure(store, mode):
    async with server_session(failure=mode == "failure") as (session, effects):
        registry = Registry()
        await MCPTools(session, MCPConfig("local", "https://fixture.example")).register(registry)
        model = ScriptedModel(
            (
                Response(
                    calls=(
                        Call(
                            id="one",
                            name="local__write",
                            arguments={"value": "bad" if mode == "invalid" else 1},
                        ),
                    ),
                    finish="tool_calls",
                ),
                Response(text="done"),
            )
        )
        policy = (
            Policy()
            if mode == "denied"
            else Policy(
                allowed_tools=frozenset({"local__write"}),
                permissions=frozenset({"mcp:local__write"}),
                approve_writes=False,
            )
        )
        runtime = Runtime(model, registry, store, policy)
        run = await runtime.run("work")
        if mode == "failure":
            assert run.status == Status.UNCERTAIN and effects == [1]
            await runtime.resume(run.id)
            assert effects == [1]
        else:
            assert effects == []
            assert not any(e.kind == "tool.dispatched" for e in store.events(run.id))


@pytest.mark.parametrize(
    "kwargs",
    [
        {"url": "http://remote.example"},
        {"namespace": "../bad"},
        {"timeout": float("nan")},
        {"max_pages": 0},
        {"max_tools": 0},
        {"result_bytes": 1},
        {"url": "https://user:password@fixture.example"},
    ],
)
def test_mcp_configuration_bounds(kwargs):
    values = {"namespace": "local", "url": "https://fixture.example", **kwargs}
    with pytest.raises(ValueError):
        MCPConfig(**values)
    assert MCPConfig("local", "http://127.0.0.1/mcp", allow_local_http=True)


@pytest.mark.parametrize("json_response", [False, True])
async def test_streamable_http_connection_lifecycle_and_local_server(json_response):
    import asyncio
    import socket

    import uvicorn
    from mcp.server.fastmcp import FastMCP

    from agent_core.mcp import connect

    server = FastMCP("agent-core-http-fixture", stateless_http=True, json_response=json_response)

    @server.tool()
    async def echo(value: int) -> int:
        return value

    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    port = listener.getsockname()[1]
    http = uvicorn.Server(uvicorn.Config(server.streamable_http_app(), log_level="error"))
    task = asyncio.create_task(http.serve(sockets=[listener]))
    try:
        async with asyncio.timeout(5):
            while not http.started:
                if task.done():
                    await task
                await asyncio.sleep(0.01)
        config = MCPConfig("http", f"http://127.0.0.1:{port}/mcp", allow_local_http=True)
        async with connect(config) as bridge:
            registry = Registry()
            assert await bridge.register(registry) == ("http__echo",)
            result = await registry.get("http__echo").function(value=7)
            assert result["structuredContent"] == {"result": 7}
        assert bridge.closed
    finally:
        http.should_exit = True
        await task
        listener.close()


@pytest.mark.parametrize(
    "case", ["duplicate", "tool_limit", "page_limit", "cursor", "schema", "error"]
)
async def test_mcp_discovery_limits_are_atomic(case):
    class Session:
        async def list_tools(self, cursor=None):
            if case == "error":
                raise ValueError("private details")
            schema = {"type": "object"}
            if case == "schema":
                schema["$ref"] = "https://untrusted.example/schema"
            tool = types.Tool(name="tool", inputSchema=schema)
            if case == "duplicate":
                return types.ListToolsResult(tools=[tool, tool])
            if case in {"page_limit", "cursor"}:
                return types.ListToolsResult(tools=[] if cursor else [tool], nextCursor="next")
            return types.ListToolsResult(tools=[tool, types.Tool(name="other", inputSchema=schema)])

    config = MCPConfig(
        "local",
        "https://fixture.example",
        max_tools=1 if case == "tool_limit" else 128,
        max_pages=1 if case == "page_limit" else 8,
    )
    registry = Registry()
    with pytest.raises(CoreError):
        await MCPTools(Session(), config).register(registry)
    assert registry.all() == ()


@pytest.mark.parametrize("case", ["closed", "large", "output", "error", "timeout"])
async def test_mcp_execution_errors_bounded(case):
    import asyncio

    class Session:
        async def call_tool(self, name, arguments):
            if case == "timeout":
                await asyncio.Event().wait()
            if case == "error":
                raise ValueError("private failure")
            return types.CallToolResult(content=[types.TextContent(type="text", text="x" * 1024)])

    bridge = MCPTools(
        Session(), MCPConfig("local", "https://fixture.example", timeout=0.01, result_bytes=128)
    )
    bridge.closed = case == "closed"
    with pytest.raises(CoreError):
        await bridge._execute("tool", {"type": "object"} if case == "output" else None)
