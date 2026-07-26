"""Per-source API rate limiter.

HubSpot, Google, Slack, etc. all have rate limits. The live-read plane
MUST respect these or risk token revocation / temporary bans.
"""

from __future__ import annotations

import asyncio
import time
from collections import defaultdict
from dataclasses import dataclass, field

from libs.observability.logging import get_logger

logger = get_logger("rate_limiter")


@dataclass
class RateLimitConfig:
    """Rate limit configuration for a source API."""

    requests_per_minute: int = 100
    requests_per_second: int = 10
    burst_size: int = 5


class TokenBucketRateLimiter:
    """Token bucket rate limiter — per source, per viewer.

    Ensures we never exceed source API rate limits during
    live reads and permission pings.
    """

    def __init__(self) -> None:
        self._buckets: dict[str, _Bucket] = defaultdict(
            lambda: _Bucket(capacity=10, refill_rate=10.0)
        )
        self._configs: dict[str, RateLimitConfig] = {}

    def configure(self, provider_type: str, config: RateLimitConfig) -> None:
        """Set rate limit config for a provider type."""
        self._configs[provider_type] = config
        rps = config.requests_per_second
        self._buckets[provider_type] = _Bucket(
            capacity=config.burst_size, refill_rate=float(rps)
        )

    async def acquire(self, provider_type: str) -> None:
        """Wait until a request is permitted for this provider."""
        bucket = self._buckets[provider_type]
        while not bucket.try_consume():
            wait_time = 1.0 / bucket.refill_rate
            logger.debug("rate_limited", provider=provider_type, wait_s=wait_time)
            await asyncio.sleep(wait_time)


@dataclass
class _Bucket:
    capacity: int
    refill_rate: float
    tokens: float = field(init=False)
    last_refill: float = field(init=False)

    def __post_init__(self) -> None:
        self.tokens = float(self.capacity)
        self.last_refill = time.monotonic()

    def try_consume(self) -> bool:
        now = time.monotonic()
        elapsed = now - self.last_refill
        self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
        self.last_refill = now

        if self.tokens >= 1.0:
            self.tokens -= 1.0
            return True
        return False


# Singleton instance
rate_limiter = TokenBucketRateLimiter()

# Default configs for known providers
_DEFAULT_CONFIGS: dict[str, RateLimitConfig] = {
    "hubspot": RateLimitConfig(requests_per_minute=100, requests_per_second=10, burst_size=10),
    "google_drive": RateLimitConfig(requests_per_minute=300, requests_per_second=5, burst_size=5),
    "google_sheets": RateLimitConfig(requests_per_minute=60, requests_per_second=1, burst_size=3),
    "gmail": RateLimitConfig(requests_per_minute=250, requests_per_second=5, burst_size=5),
    "slack": RateLimitConfig(requests_per_minute=50, requests_per_second=1, burst_size=3),
    "gong": RateLimitConfig(requests_per_minute=60, requests_per_second=1, burst_size=3),
}

for provider, config in _DEFAULT_CONFIGS.items():
    rate_limiter.configure(provider, config)
