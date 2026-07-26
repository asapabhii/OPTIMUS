"""Store adapter — abstract interface for the primary data store.

Commercial: Neon (managed Postgres 16)
OSS fallback: Plain Postgres 16 (dump/restore — vanilla Postgres throughout)
"""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from typing import Any

from core.enums import VisibilityLevel
from core.models.entity import Entity, EntityLink


class StoreAdapter(ABC):
    """Abstract store interface.

    All implementations MUST enforce:
    - RLS via viewer_id on every table
    - The no_live_values CHECK constraint
    - Bitemporal columns on declarations
    """

    @abstractmethod
    async def set_viewer_context(self, viewer_id: uuid.UUID) -> None:
        """Set the current viewer for RLS policies."""

    @abstractmethod
    async def get_entity(self, entity_id: uuid.UUID) -> Entity | None:
        """Get an entity by ID (filtered by current viewer's RLS)."""

    @abstractmethod
    async def search_entities(
        self, query: str, entity_type: str | None = None, limit: int = 20
    ) -> list[Entity]:
        """Search entities by name or type."""

    @abstractmethod
    async def upsert_entity(self, entity: Entity) -> Entity:
        """Insert or update an entity."""

    @abstractmethod
    async def get_entity_links(self, entity_id: uuid.UUID) -> list[EntityLink]:
        """Get all links for an entity."""

    @abstractmethod
    async def execute_raw(self, query: str, params: dict[str, Any] | None = None) -> Any:
        """Execute a raw query (for recursive CTEs, graph traversal)."""

    @abstractmethod
    async def health_check(self) -> bool:
        """Liveness check."""
