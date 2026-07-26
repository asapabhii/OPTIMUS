"""Vector store adapter — abstract interface for evidence search.

Commercial: Qdrant Cloud (per-viewer collections, ACL-in-predicate)
OSS fallback: Qdrant OSS (Apache 2.0, same engine)
Future fallback: Turbopuffer (namespace-per-viewer) on measured need
"""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class VectorDocument:
    """A document to index in the vector store."""

    id: str
    content: str
    embedding: list[float] | None = None
    metadata: dict[str, str] = field(default_factory=dict)
    viewer_id: str = ""


@dataclass
class VectorSearchResult:
    """A search result from the vector store."""

    id: str
    content: str
    score: float
    metadata: dict[str, str] = field(default_factory=dict)


class VectorAdapter(ABC):
    """Abstract vector store.

    Implementations MUST:
    - Maintain per-viewer collections (per-viewer isolation)
    - Support ACL-in-predicate filtering
    - Never serve one viewer's indexed content to another
    """

    @abstractmethod
    async def ensure_collection(self, viewer_id: uuid.UUID) -> None:
        """Ensure a per-viewer collection exists."""

    @abstractmethod
    async def upsert(self, viewer_id: uuid.UUID, documents: list[VectorDocument]) -> None:
        """Upsert documents into a viewer's collection."""

    @abstractmethod
    async def search(
        self,
        viewer_id: uuid.UUID,
        query: str,
        limit: int = 10,
        filter_metadata: dict[str, str] | None = None,
    ) -> list[VectorSearchResult]:
        """Search a viewer's collection."""

    @abstractmethod
    async def delete(self, viewer_id: uuid.UUID, document_ids: list[str]) -> None:
        """Delete documents from a viewer's collection."""

    @abstractmethod
    async def health_check(self) -> bool:
        """Liveness check."""
