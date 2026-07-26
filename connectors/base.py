"""Connector interface — the contract every source connector must fulfill.

Works with ANY Nango integration. Specialized overrides exist only
where source-specific logic is needed (sheet semantics, CRM mapping).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from core.enums import SourceClass, VolatilityClass


@dataclass
class IngestedItem:
    """A single item ingested from a source."""

    source_ref: str
    content: str
    item_type: str  # email, document, transcript, deal, contact, etc.
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = ""
    updated_at: str = ""


@dataclass
class LiveReadResult:
    """Result of a live read from a source."""

    source_ref: str
    value: Any
    fetched_at: str
    is_accessible: bool = True
    error: str | None = None


@dataclass
class PermissionPingResult:
    """Result of a permission ping — can this viewer see this item?"""

    source_ref: str
    is_accessible: bool
    checked_at: str


class ConnectorInterface(ABC):
    """The contract for source connectors.

    Every connector must support:
    1. Fast-path ingestion (first-N most-recent items)
    2. Full batch ingestion
    3. Live reads (for authority sources with live-state data)
    4. Permission pings (can this viewer see this specific item?)
    """

    provider_type: str
    default_source_class: SourceClass
    default_volatility: VolatilityClass

    @abstractmethod
    async def ingest_fast_path(
        self, connection_id: str, limit: int = 50
    ) -> list[IngestedItem]:
        """Fast-path ingestion: most-recent N items for the onboarding wow moment."""

    @abstractmethod
    async def ingest_full(
        self, connection_id: str, depth_days: int = 365
    ) -> list[IngestedItem]:
        """Full batch ingestion: all items within the backfill depth."""

    @abstractmethod
    async def live_read(
        self, connection_id: str, source_ref: str
    ) -> LiveReadResult:
        """Live read: fetch the current value from the source.

        Only sources with live-state data need this.
        Uses the viewer's own Nango-managed token.
        """

    @abstractmethod
    async def permission_ping(
        self, connection_id: str, source_ref: str
    ) -> PermissionPingResult:
        """Permission ping: can this viewer see this specific item?

        Every rendered claim is permission-verified at the source,
        as the viewer, during the turn (P21).
        """
