"""Invalidation worker — webhook-driven staleness marking.

Consumes from: source.changed
Action: mark stale, bump version_counter, trigger lazy re-derivation

When a source change webhook fires:
1. Mark affected source_entity_links as stale
2. Bump version_counter
3. If dependent beliefs exist: mark them stale (lazy re-derivation)
4. Belief recomputation happens at next query time (not eagerly)
"""

from __future__ import annotations

import asyncio

from libs.adapters.events import Event, EventBusAdapter
from libs.config.settings import get_settings
from libs.observability.logging import setup_logging, get_logger

logger = get_logger("invalidation")

TOPIC_SOURCE_CHANGED = "source.changed"


async def process_source_changed(event: Event) -> None:
    """Process a source.changed event.

    Steps:
    1. Find all source_entity_links for this source + source_ref
    2. Mark as stale + bump version_counter
    3. Find all beliefs that depend on these links
    4. Mark those beliefs as stale (lazy — recomputed on next query)
    """
    source_id = event.value.get("source_id", "")
    source_ref = event.value.get("source_ref", "")
    change_type = event.value.get("change_type", "updated")

    logger.info(
        "source_changed",
        source_id=source_id,
        source_ref=source_ref,
        change_type=change_type,
    )

    # TODO: Wire to store adapter:
    # 1. UPDATE source_entity_links SET is_stale = true, version_counter = version_counter + 1
    #    WHERE source_id = ? AND source_ref = ?
    # 2. UPDATE beliefs SET is_stale = true
    #    WHERE evidence_ids && (SELECT ARRAY_AGG(id) FROM source_entity_links WHERE ...)


async def main() -> None:
    """Start the invalidation worker."""
    setup_logging()
    settings = get_settings()

    logger.info("invalidation_worker_starting", env=settings.app_env)

    # TODO: Subscribe to source.changed topic via EventBusAdapter
    while True:
        await asyncio.sleep(60)
        logger.debug("invalidation_heartbeat")


if __name__ == "__main__":
    asyncio.run(main())
