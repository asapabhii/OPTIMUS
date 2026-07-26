"""Fast-path worker (G1) — priority lane for onboarding.

Consumes from: fast_path.{provider_type}
Produces to: candidates.structural (for reconciliation)

Processes the first-N most-recent items for the "wow moment":
- Visible graph build during onboarding
- Fast entity resolution while user watches
- Background full ingestion continues after fast path completes

This worker has a SEPARATE Redpanda topic with higher priority
to ensure it is never starved by batch ingestion.
"""

from __future__ import annotations

import uuid

from libs.adapters.events import Event, EventBusAdapter
from libs.observability.logging import get_logger

logger = get_logger("worker.fast_path")

TOPIC_PREFIX = "fast_path"
TOPIC_CANDIDATES = "candidates.structural"


async def process_fast_path_event(
    event: Event,
    event_bus: EventBusAdapter,
) -> None:
    """Process a fast-path ingestion event.

    Steps:
    1. Parse the first-N items
    2. Extract entities and facts
    3. Publish candidates for immediate reconciliation
    4. Update onboarding status (progress bar)
    """
    source_id = event.value.get("source_id", "")
    viewer_id = event.value.get("viewer_id", "")
    items = event.value.get("items", [])
    limit = event.value.get("limit", 50)

    logger.info(
        "fast_path_processing",
        source_id=source_id,
        item_count=len(items),
        limit=limit,
    )

    # TODO: Parse → extract → publish candidates
    # Each extracted entity becomes a candidate for reconciliation.
    # The frontend polls onboarding status to show visible graph build.

    for item in items:
        await event_bus.publish(
            Event(
                topic=TOPIC_CANDIDATES,
                key=str(viewer_id),
                value={
                    "source_id": source_id,
                    "source_ref": item.get("source_ref", ""),
                    "extracted_name": item.get("name", ""),
                    "entity_type": item.get("entity_type", "unknown"),
                    "viewer_id": viewer_id,
                    "is_fast_path": True,
                },
            )
        )

    logger.info(
        "fast_path_complete",
        source_id=source_id,
        candidates_published=len(items),
    )
