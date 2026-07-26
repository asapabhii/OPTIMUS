"""Staging — the entry point for the reconciliation engine.

New source structure arrives here as staged candidates.
They are NEVER answerable (REQ-3.6a) until the three-way sort
has resolved them.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from libs.observability.logging import get_logger

logger = get_logger("reconciliation.staging")


@dataclass
class StagedCandidate:
    """A candidate entity extracted from a source, not yet reconciled."""

    id: uuid.UUID
    source_id: uuid.UUID
    source_ref: str
    extracted_name: str
    entity_type: str
    attributes: dict[str, str]
    viewer_id: uuid.UUID


async def stage_candidates(
    candidates: list[StagedCandidate],
) -> list[uuid.UUID]:
    """Stage candidates for reconciliation.

    These are persisted but NEVER answerable until sorted.
    The three-way sort processes them asynchronously.

    TODO: Wire to staged_candidates table via store adapter.
    """
    staged_ids = [c.id for c in candidates]
    logger.info(
        "candidates_staged",
        count=len(candidates),
        viewer_id=str(candidates[0].viewer_id) if candidates else "unknown",
    )
    return staged_ids
