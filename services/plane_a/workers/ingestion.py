"""Ingestion worker — receives raw documents from the event bus.

Consumes from: raw.documents
Produces to: parsed.units (for parsing worker)

Part of Plane A only. Structurally separate from Plane B.
"""

from __future__ import annotations

from libs.adapters.events import Event, EventBusAdapter
from libs.observability.logging import get_logger

logger = get_logger("worker.ingestion")

TOPIC_RAW = "raw.documents"
TOPIC_PARSED = "parsed.units"


async def process_ingestion_event(
    event: Event,
    event_bus: EventBusAdapter,
) -> None:
    """Process a raw document ingestion event.

    Steps:
    1. Check extraction cache (content-hash dedup)
    2. If cache miss: publish to parsing topic
    3. If cache hit: skip parsing, proceed to extraction
    """
    source_ref = event.value.get("source_ref", "")
    content_hash = event.value.get("content_hash", "")
    viewer_id = event.value.get("viewer_id", "")

    logger.info(
        "ingestion_received",
        source_ref=source_ref,
        content_hash=content_hash[:16],
    )

    # TODO: Check extraction_cache for content_hash
    # If cache hit: skip to reconciliation
    # If cache miss: publish to parsed.units topic

    await event_bus.publish(
        Event(
            topic=TOPIC_PARSED,
            key=source_ref,
            value={
                "source_ref": source_ref,
                "content_hash": content_hash,
                "viewer_id": viewer_id,
            },
        )
    )
