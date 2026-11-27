import asyncio

import pytest

from agent_core import CoreError
from agent_core.providers.sse import Frame, frames


async def chunks(parts):
    for part in parts:
        yield part


@pytest.mark.parametrize("separator", ["\n", "\r\n", "\r"])
@pytest.mark.parametrize("width", [1, 2, 1000])
async def test_incremental_sse_framing(separator, width):
    wire = (
        "\ufeff: heartbeat"
        + separator
        + "event: delta"
        + separator
        + "data: Я"
        + separator
        + "data: two"
        + separator
        + separator
    ).encode()
    result = [
        frame
        async for frame in frames(
            chunks([wire[i : i + width] for i in range(0, len(wire), width)]),
            byte_limit=1024,
        )
    ]
    assert result == [Frame("delta", "Я\ntwo")]


@pytest.mark.parametrize("wire", [b"data: partial", b"data: partial\n", b"data: \xff\n\n", b"\xc3"])
async def test_truncated_and_invalid_sse_rejected(wire):
    with pytest.raises(CoreError, match="provider_response"):
        _ = [frame async for frame in frames(chunks([wire]), byte_limit=128)]


async def test_sse_bounds_and_pull_backpressure():
    consumed = []

    async def source():
        for i in range(3):
            consumed.append(i)
            yield b"data: value\n\n"

    stream = frames(source(), byte_limit=128)
    assert (await anext(stream)).data == "value"
    assert consumed == [0]
    await stream.aclose()
    assert consumed == [0]
    with pytest.raises(CoreError):
        _ = [frame async for frame in frames(chunks([b"x" * 129]), byte_limit=128)]
    with pytest.raises(ValueError):
        await anext(frames(chunks([]), byte_limit=0))


async def test_sse_empty_data_unknown_fields_and_cancellation():
    wire = b"id: 1\nretry: 10\nunknown\ndata\n\n"
    assert [f async for f in frames(chunks([wire]), byte_limit=128)] == [Frame("message", "")]
    started = asyncio.Event()

    async def waiting():
        started.set()
        await asyncio.Event().wait()
        yield b""

    stream = frames(waiting(), byte_limit=128)
    task = asyncio.create_task(anext(stream))
    await started.wait()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    await stream.aclose()
