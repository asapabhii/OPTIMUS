"""Non-blocking merger — processes sorted candidates.

Novel entities are created immediately.
Confident matches are auto-merged, logged, and reversible.
Conflicts are surfaced in the review queue without blocking ingestion.

Un-merge is implemented via merged_into + resolver record delete/re-resolve.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from core.enums import AutoDecisionType, SortOutcome
from core.models.decision import AutoDecision
from core.models.entity import Entity
from engine.reconciliation.sorter import SortResult
from libs.observability.logging import get_logger

logger = get_logger("reconciliation.merger")


async def process_sort_results(
    results: list[SortResult],
) -> dict[str, list[uuid.UUID]]:
    """Process the three-way sort output.

    Returns:
        Dict with keys 'created', 'merged', 'conflicted'
        each mapping to a list of entity IDs.
    """
    created: list[uuid.UUID] = []
    merged: list[uuid.UUID] = []
    conflicted: list[uuid.UUID] = []

    for result in results:
        if result.outcome == SortOutcome.NOVEL:
            entity_id = await _create_entity(result)
            created.append(entity_id)

        elif result.outcome == SortOutcome.CONFIDENT_MATCH:
            assert result.matched_entity_id is not None
            await _auto_merge(result)
            merged.append(result.matched_entity_id)

        elif result.outcome == SortOutcome.CONFLICT:
            conflict_id = await _escalate_conflict(result)
            conflicted.append(conflict_id)

    logger.info(
        "merge_batch_complete",
        created=len(created),
        merged=len(merged),
        conflicted=len(conflicted),
    )

    return {
        "created": created,
        "merged": merged,
        "conflicted": conflicted,
    }


async def _create_entity(result: SortResult) -> uuid.UUID:
    """Create a new entity for a novel candidate."""
    entity = Entity(
        canonical_name=result.candidate.extracted_name,
        entity_type=result.candidate.entity_type,
        viewer_id=result.candidate.viewer_id,
    )
    logger.info("entity_created", name=entity.canonical_name, id=str(entity.id))
    # TODO: Persist via store adapter
    return entity.id


async def _auto_merge(result: SortResult) -> None:
    """Auto-merge a confident match — logged and reversible (REQ-11.2)."""
    decision = AutoDecision(
        decision_type=AutoDecisionType.ENTITY_MERGE,
        input_data={
            "candidate_name": result.candidate.extracted_name,
            "matched_entity_id": str(result.matched_entity_id),
        },
        output_data={
            "merged": True,
            "merged_into": str(result.matched_entity_id),
        },
        explanation=result.explanation,
        confidence=result.confidence,
        viewer_id=result.candidate.viewer_id,
    )
    logger.info(
        "entity_auto_merged",
        candidate=result.candidate.extracted_name,
        into=str(result.matched_entity_id),
        confidence=result.confidence,
    )
    # TODO: Persist decision + update entity.merged_into via store adapter


async def _escalate_conflict(result: SortResult) -> uuid.UUID:
    """Escalate an ambiguous match to the review queue (non-blocking)."""
    conflict_id = uuid.uuid4()
    logger.info(
        "entity_conflict_escalated",
        candidate=result.candidate.extracted_name,
        conflict_id=str(conflict_id),
        confidence=result.confidence,
    )
    # TODO: Write to review queue (staged_candidates.sort_outcome = 'conflict')
    return conflict_id


async def unmerge(
    entity_id: uuid.UUID,
    record_id: str,
    viewer_id: uuid.UUID,
) -> list[uuid.UUID]:
    """Un-merge: reverse a merge by deleting the record and re-resolving.

    Sets merged_into=NULL on the entity and triggers resolver re-resolve
    on all affected entities (REQ-11.2b).

    TODO: Wire to ResolverAdapter.unmerge + store adapter.
    """
    logger.info(
        "entity_unmerge",
        entity_id=str(entity_id),
        record_id=record_id,
    )
    return [entity_id]
