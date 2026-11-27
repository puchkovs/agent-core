"""Bounded complete-response HTTP transport, without automatic retries."""

from __future__ import annotations

import json
import math
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlsplit

import httpx

from agent_core.contracts import CoreError, Json, canonical

from .sse import Frame, frames


@dataclass(frozen=True)
class Capabilities:
    tools: bool = True
    lifecycle_stream: bool = True
    token_deltas: bool = False
    native_output_schema: bool = False
    images: bool = False


class Transport:
    def __init__(
        self,
        *,
        client: httpx.AsyncClient | None = None,
        response_bytes: int = 1048576,
        timeout: float = 60,
    ):
        self.client = client
        self.response_bytes = response_bytes
        self.timeout = timeout
        if response_bytes < 128 or not math.isfinite(timeout) or timeout <= 0:
            raise ValueError("invalid transport bounds")

    async def post(
        self, url: str, headers: dict[str, str], payload: dict[str, Json]
    ) -> dict[str, Json]:
        if urlsplit(url).scheme != "https":
            raise CoreError("provider_configuration")
        client = self.client or httpx.AsyncClient(follow_redirects=False, trust_env=False)
        try:
            async with client.stream(
                "POST",
                url,
                headers=headers,
                json=payload,
                timeout=self.timeout,
                follow_redirects=False,
            ) as response:
                status = response.status_code
                if status in {401, 403}:
                    raise CoreError("provider_auth")
                if status == 429:
                    raise CoreError("provider_rate_limit", retryable=True)
                if status >= 500:
                    raise CoreError("provider_unavailable", retryable=True)
                if status < 200 or status >= 300:
                    raise CoreError("provider_response")
                buffer = bytearray()
                async for chunk in response.aiter_bytes():
                    if len(buffer) + len(chunk) > self.response_bytes:
                        raise CoreError("provider_response")
                    buffer.extend(chunk)
                decoded = json.loads(buffer, object_pairs_hook=unique_object)
                if not isinstance(decoded, dict):
                    raise CoreError("provider_response")
                canonical(decoded)
                return decoded
        except httpx.HTTPError as exc:
            raise CoreError("provider_transport", retryable=True) from exc
        except (UnicodeError, ValueError, RecursionError) as exc:
            raise CoreError("provider_response") from exc
        finally:
            if self.client is None:
                await client.aclose()

    async def stream(
        self, url: str, headers: dict[str, str], payload: dict[str, Json]
    ) -> AsyncIterator[Frame]:
        if urlsplit(url).scheme != "https":
            raise CoreError("provider_configuration")
        client = self.client or httpx.AsyncClient(follow_redirects=False, trust_env=False)
        try:
            async with client.stream(
                "POST",
                url,
                headers=headers,
                json=payload,
                timeout=self.timeout,
                follow_redirects=False,
            ) as response:
                status = response.status_code
                if status in {401, 403}:
                    raise CoreError("provider_auth")
                if status == 429:
                    raise CoreError("provider_rate_limit", retryable=True)
                if status >= 500:
                    raise CoreError("provider_unavailable", retryable=True)
                if status < 200 or status >= 300:
                    raise CoreError("provider_response")
                if response.headers.get("content-type", "").split(";")[0] != "text/event-stream":
                    raise CoreError("provider_response")
                async for frame in frames(response.aiter_bytes(), byte_limit=self.response_bytes):
                    yield frame
        except httpx.HTTPError as exc:
            raise CoreError("provider_transport", retryable=True) from exc
        finally:
            if self.client is None:
                await client.aclose()


def parse_arguments(value: Any) -> dict[str, Json]:
    if not isinstance(value, str):
        raise CoreError("provider_response")

    try:
        parsed = json.loads(value, object_pairs_hook=unique_object)
        canonical(parsed)
        if not isinstance(parsed, dict):
            raise ValueError("arguments must be object")
        return parsed
    except (TypeError, ValueError, RecursionError) as exc:
        raise CoreError("provider_response") from exc


def unique_object(items: list[tuple[str, Json]]) -> dict[str, Json]:
    result: dict[str, Json] = {}
    for key, item in items:
        if key in result:
            raise ValueError("duplicate argument key")
        result[key] = item
    return result


def usage_count(value: Json) -> int | None:
    """Keep absent accounting unknown; never coerce provider counters."""
    if value is None:
        return None
    if type(value) is not int or value < 0:
        raise ValueError("invalid token count")
    return value
