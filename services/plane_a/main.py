"""Plane A — async batch workers entry point.

Structurally separate from Plane B. A backed-up sync degrades
structure freshness ONLY — it is incapable of slowing a live read.

Workers:
1. Ingestion: receives raw documents from event bus
2. Fast-path: priority lane for onboarding (G1)
3. Parsing: document decomposition via LlamaCloud
4. Extraction: structured extraction via Portkey
5. Reconciliation: triggers Temporal workflow
6. Indexing: Qdrant per-viewer upserts
"""

from __future__ import annotations

import asyncio

from libs.config.settings import get_settings
from libs.observability.logging import setup_logging, get_logger
from libs.observability.tracing import setup_tracing
from libs.observability.metrics import setup_metrics

logger = get_logger("plane_a")


async def main() -> None:
    """Start all Plane A workers."""
    settings = get_settings()
    setup_logging()
    setup_tracing()
    setup_metrics()

    logger.info(
        "plane_a_starting",
        env=settings.app_env,
        workers=["ingestion", "fast_path", "parsing", "extraction", "reconciliation", "indexing"],
    )

    # TODO: Start consumer loops for each worker
    # Each worker subscribes to its Redpanda topic and processes events.
    # Fast-path worker has a SEPARATE priority topic for onboarding.

    # For now, keep the process alive
    while True:
        await asyncio.sleep(60)
        logger.debug("plane_a_heartbeat")


if __name__ == "__main__":
    asyncio.run(main())
