"""Entity resolver adapter — abstract interface for entity resolution.

Primary: Splink (MIT, probabilistic record linkage) + RapidFuzz (MIT, fuzzy matching)
Alternative: dedupe (MIT, ML-based deduplication)

The Gate-1 stop-test (>=0.98 auto-merge precision on ~200 labeled pairs)
validates the implementation EMPIRICALLY. Both options are free and open source.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class ResolveCandidate:
    """An entity candidate extracted from a source."""

    name: str
    entity_type: str
    source_id: str
    source_ref: str
    attributes: dict[str, str]


@dataclass
class ResolveResult:
    """Result of resolving a candidate against existing entities."""

    candidate: ResolveCandidate
    matched_entity_id: str | None
    confidence: float
    explanation: str  # Splink match breakdown or fuzzy reasoning
    is_novel: bool
    is_conflict: bool


@dataclass
class WhyExplanation:
    """Match explanation — rendered in the review queue.

    Produces "matched on domain, differ on legal suffix" — the explanation
    the review queue requires, instead of a number we must translate.
    Splink provides comparison vectors; we translate them to natural language.
    """

    match_key: str
    match_details: list[dict[str, str]]
    why_text: str


class ResolverAdapter(ABC):
    """Abstract entity resolver.

    Implementations MUST:
    - Support incremental resolve (record-by-record, no batch wait)
    - Produce explainable match results (for the review queue)
    - Support un-merge (record delete/re-resolve)
    - Run in-process (data never leaves our boundary)
    """

    @abstractmethod
    async def resolve(self, candidate: ResolveCandidate) -> ResolveResult:
        """Resolve a single candidate against the existing entity set."""

    @abstractmethod
    async def resolve_batch(self, candidates: list[ResolveCandidate]) -> list[ResolveResult]:
        """Resolve a batch of candidates."""

    @abstractmethod
    async def why(self, entity_id_1: str, entity_id_2: str) -> WhyExplanation:
        """Explain why two entities were (or were not) merged."""

    @abstractmethod
    async def unmerge(self, entity_id: str, record_id: str) -> list[ResolveResult]:
        """Un-merge: delete a record and re-resolve affected entities."""

    @abstractmethod
    async def health_check(self) -> bool:
        """Liveness check."""
