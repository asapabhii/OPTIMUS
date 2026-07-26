"""Ingestion adapter — abstract interface for batch data ingestion.

Commercial: Airbyte Cloud
OSS fallback: Airbyte OSS

Plane A only. A backed-up sync degrades structure freshness only —
it is structurally incapable of slowing a live read (REQ-4.3).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class SyncJob:
    """A batch sync job."""

    job_id: str
    connection_id: str
    status: str  # pending, running, completed, failed
    records_synced: int = 0
    started_at: str | None = None
    completed_at: str | None = None


class IngestionAdapter(ABC):
    """Abstract batch ingestion."""

    @abstractmethod
    async def create_connection(
        self,
        source_type: str,
        config: dict[str, Any],
    ) -> str:
        """Create an ingestion connection. Returns connection_id."""

    @abstractmethod
    async def trigger_sync(self, connection_id: str) -> SyncJob:
        """Trigger a sync job for a connection."""

    @abstractmethod
    async def get_sync_status(self, job_id: str) -> SyncJob:
        """Get the status of a sync job."""

    @abstractmethod
    async def health_check(self) -> bool:
        """Liveness check."""
