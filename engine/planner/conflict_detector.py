"""Conflict detector — detects and surfaces disagreements across sources.

Conflicts are NEVER silently resolved (REQ-8.3).
Both values are shown, along with which won and the arbitration rule.
The conflict the system already detected to answer correctly
IS the promotion trigger (REQ-6.2).
"""

from __future__ import annotations

import uuid

from core.models.answer import ConflictBlock
from libs.observability.logging import get_logger
from libs.observability.metrics import conflicts_surfaced

logger = get_logger("planner.conflict_detector")


async def detect_conflicts(
    fan_out_data: dict[str, list[dict[str, str]]],
    entity_id: uuid.UUID,
    viewer_id: uuid.UUID,
) -> list[ConflictBlock]:
    """Detect conflicts across sources for an entity.

    A conflict occurs when two sources disagree about the same fact.
    The arbitration rule is stated in natural language, not as a number.

    Example:
    "Showing the spreadsheet — it is your declared system of record
    for renewals — last edited 2 days ago; the deck's figure is
    8 months old."

    TODO: Implement comparison logic across declarations, held values,
    and live reads. Use the freshness table and SoR declarations for
    arbitration.
    """
    conflicts: list[ConflictBlock] = []

    # Compare declarations vs held values
    # Compare held values vs live reads
    # Compare live reads across sources

    if conflicts:
        conflicts_surfaced.add(len(conflicts), {"viewer_id": str(viewer_id)})
        logger.info(
            "conflicts_detected",
            entity_id=str(entity_id),
            count=len(conflicts),
        )

    return conflicts
