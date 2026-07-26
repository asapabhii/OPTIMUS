"""Event bus adapter — abstract interface for async messaging.

Commercial: Redpanda Cloud Serverless
OSS fallback: Redpanda OSS / Kafka (same protocol)

Plane isolation is enforced via separate topics:
- raw.documents (Plane A batch)
- fast_path.{provider_type} (Plane A priority — onboarding)
- candidates.structural (Plane A extraction output)
- source.changed (webhooks → invalidation worker)
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, AsyncIterator, Callable


@dataclass
class Event:
    """An event on the bus."""

    topic: str
    key: str
    value: dict[str, Any]
    headers: dict[str, str] = field(default_factory=dict)


class EventBusAdapter(ABC):
    """Abstract event bus.

    The two planes share NO topics — this is how batch delays
    are structurally incapable of slowing live reads (REQ-4.3).
    """

    @abstractmethod
    async def publish(self, event: Event) -> None:
        """Publish an event to a topic."""

    @abstractmethod
    async def publish_batch(self, events: list[Event]) -> None:
        """Publish a batch of events."""

    @abstractmethod
    async def subscribe(
        self,
        topics: list[str],
        group_id: str,
        handler: Callable[[Event], Any],
    ) -> None:
        """Subscribe to topics with a consumer group."""

    @abstractmethod
    async def stream(
        self, topics: list[str], group_id: str
    ) -> AsyncIterator[Event]:
        """Stream events from topics."""

    @abstractmethod
    async def health_check(self) -> bool:
        """Liveness check."""
