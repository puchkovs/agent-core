"""Bounded incremental SSE framing; frames carry no execution authority."""

from __future__ import annotations

import codecs
from collections.abc import AsyncIterable, AsyncIterator
from dataclasses import dataclass

from agent_core.contracts import CoreError


@dataclass(frozen=True)
class Frame:
    event: str
    data: str


async def frames(chunks: AsyncIterable[bytes], *, byte_limit: int) -> AsyncIterator[Frame]:
    """Pull frames without a producer queue; reject truncated or invalid UTF-8 input.

    LF, CRLF and CR delimit lines. Comments and unknown SSE fields are ignored.
    Reconnection and event IDs are deliberately not implemented: model requests
    must never be automatically replayed after a broken stream.
    """
    if byte_limit < 1:
        raise ValueError("positive stream byte limit required")
    decoder = codecs.getincrementaldecoder("utf-8-sig")("strict")
    buffer = ""
    total = 0
    event = ""
    data: list[str] = []

    def line(value: str) -> Frame | None:
        nonlocal event, data
        if not value:
            frame = Frame(event or "message", "\n".join(data)) if data else None
            event, data = "", []
            return frame
        if value.startswith(":"):
            return None
        field, separator, content = value.partition(":")
        if separator and content.startswith(" "):
            content = content[1:]
        if field == "event":
            event = content
        elif field == "data":
            data.append(content)
        return None

    try:
        async for chunk in chunks:
            total += len(chunk)
            if total > byte_limit:
                raise CoreError("provider_response")
            buffer += decoder.decode(chunk)
            while True:
                positions = [p for p in (buffer.find("\n"), buffer.find("\r")) if p >= 0]
                if not positions:
                    break
                end = min(positions)
                if buffer[end] == "\r" and end == len(buffer) - 1:
                    break
                width = 2 if buffer[end : end + 2] == "\r\n" else 1
                value, buffer = buffer[:end], buffer[end + width :]
                if frame := line(value):
                    yield frame
        buffer += decoder.decode(b"", final=True)
        if buffer.endswith("\r"):
            if frame := line(buffer[:-1]):
                yield frame
            buffer = ""
        if buffer or data or event:
            raise CoreError("provider_response")
    except UnicodeError as exc:
        raise CoreError("provider_response") from exc
