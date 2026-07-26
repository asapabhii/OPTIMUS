"""Three-way sorter — the core of the reconciliation engine (REQ-3.6a).

Every staged candidate is sorted into exactly one of:
1. NOVEL — no existing match → create new entity
2. CONFIDENT — above threshold → auto-merge, logged, reversible
3. CONFLICT — ambiguous or contradictory → escalate to review queue

The threshold is calibrated by the Gate-1 stop-test against
the labeled corpus (>=0.98 precision).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from core.enums import AutoDecisionType, SortOutcome
from engine.reconciliation.staging import StagedCandidate
from libs.adapters.resolver import ResolveCandidate, ResolveResult, ResolverAdapter
from libs.observability.logging import get_logger

logger = get_logger("reconciliation.sorter")

# Calibrated by Gate-1 stop-test
CONFIDENCE_THRESHOLD = 0.85


@dataclass
class SortResult:
    """Result of the three-way sort for a single candidate."""

    candidate: StagedCandidate
    outcome: SortOutcome
    matched_entity_id: uuid.UUID | None = None
    confidence: float = 0.0
    explanation: str = ""


async def three_way_sort(
    candidates: list[StagedCandidate],
    resolver: ResolverAdapter,
) -> list[SortResult]:
    """Sort candidates using the entity resolver.

    Each candidate is resolved against the existing entity set.
    The result determines the next step:
    - NOVEL: create entity, merge immediately
    - CONFIDENT: auto-merge, log decision (reversible)
    - CONFLICT: surface in review queue (non-blocking)
    """
    results: list[SortResult] = []

    resolve_candidates = [
        ResolveCandidate(
            name=c.extracted_name,
            entity_type=c.entity_type,
            source_id=str(c.source_id),
            source_ref=c.source_ref,
            attributes=c.attributes,
        )
        for c in candidates
    ]

    resolve_results = await resolver.resolve_batch(resolve_candidates)

    for candidate, resolve_result in zip(candidates, resolve_results):
        if resolve_result.is_novel:
            outcome = SortOutcome.NOVEL
        elif resolve_result.confidence >= CONFIDENCE_THRESHOLD:
            outcome = SortOutcome.CONFIDENT_MATCH
        else:
            outcome = SortOutcome.CONFLICT

        matched_id = None
        if resolve_result.matched_entity_id:
            matched_id = uuid.UUID(resolve_result.matched_entity_id)

        results.append(
            SortResult(
                candidate=candidate,
                outcome=outcome,
                matched_entity_id=matched_id,
                confidence=resolve_result.confidence,
                explanation=resolve_result.explanation,
            )
        )

        logger.info(
            "candidate_sorted",
            name=candidate.extracted_name,
            outcome=outcome.value,
            confidence=resolve_result.confidence,
        )

    return results
