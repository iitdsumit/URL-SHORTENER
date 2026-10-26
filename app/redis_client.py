"""Single shared async Redis client.

`redis.asyncio` and `fakeredis.aioredis` expose the same API, so the rest of the
app is backend-agnostic. fakeredis is used in tests and the local benchmark;
a real Redis is used under Docker or cloud when valid REDIS_URL is provided.
"""
from __future__ import annotations

from typing import Any

import structlog

from app.config import get_settings

log = structlog.get_logger(__name__)

_client: Any | None = None


def get_redis() -> Any:
    global _client
    if _client is None:
        settings = get_settings()
        url = (settings.redis_url or "").strip().strip("'\"")
        is_valid_scheme = (
            url.startswith("redis://")
            or url.startswith("rediss://")
            or url.startswith("unix://")
        )

        # Fall back to in-memory fakeredis if requested, if scheme is invalid (e.g. https://),
        # or if in production with the default unreachable localhost.
        should_use_fake = (
            settings.use_fake_redis
            or not is_valid_scheme
            or (
                url in ("redis://localhost:6379/0", "redis://localhost:6379")
                and settings.environment == "production"
            )
        )

        if should_use_fake:
            import fakeredis.aioredis as fakeredis

            if not is_valid_scheme and url:
                log.warning(
                    "redis_invalid_scheme_fallback",
                    url=url,
                    hint="REDIS_URL must use rediss:// (e.g. rediss://default:pass@host:6379), not https://. Falling back to in-memory fakeredis.",
                )
            else:
                log.info("redis_init_fakeredis", reason="in-memory fallback active")
            _client = fakeredis.FakeRedis(decode_responses=True)
        else:
            import redis.asyncio as redis

            log.info("redis_init_network", target=url.split("@")[-1])
            _client = redis.from_url(url, decode_responses=True)
    return _client


async def close_redis() -> None:
    global _client
    if _client is not None:
        await _client.aclose()
    _client = None


def reset_redis_for_tests() -> None:
    """Drop the cached client so a fresh fakeredis is created (test isolation)."""
    global _client
    _client = None
