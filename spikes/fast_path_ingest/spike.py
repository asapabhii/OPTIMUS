"""G1 spike: Fast-path ingestion — priority lane for onboarding.

THE TEST: Verify that the fast-path lane processes first-N items
ahead of batch backfill, and that the onboarding experience completes
entity resolution within the 15-minute budget.

Validates:
1. Priority Redpanda topic processes ahead of batch topic
2. Configurable first-N per source type
3. Extraction runs immediately (not queued behind batch)
4. Entities appear in the graph within seconds, not minutes
5. Background backfill continues after fast path completes

Success criteria:
  - First entities visible within 30 seconds of source connection
  - All first-N items processed within 2 minutes
  - Batch backfill starts after fast path, does not block it
"""

from __future__ import annotations

import asyncio
import time

from connectors.backfill_policy import get_backfill_config


async def run_spike() -> None:
    """Run the fast-path ingestion spike."""

    # Step 1: Show configured limits per source type
    print("Fast-path configuration:")
    for provider in ["hubspot", "google_sheets", "gmail", "slack", "gong", "notion"]:
        config = get_backfill_config(provider)
        print(f"  {provider}: first-N={config.fast_path_n}, "
              f"backfill_days={config.backfill_depth_days}, "
              f"max_items={config.max_items or 'unlimited'}")

    # Step 2: Simulate fast-path ingestion timing
    # TODO: Connect to a real source via Nango, trigger fast-path,
    # and measure time-to-first-entity
    #
    # async with NangoConnector(credential_adapter, "hubspot") as connector:
    #     start = time.monotonic()
    #     items = await connector.ingest_fast_path(connection_id, limit=50)
    #     elapsed = time.monotonic() - start
    #     print(f"  Fast-path ingested {len(items)} items in {elapsed:.1f}s")
    #
    #     # Publish to priority topic
    #     for item in items:
    #         await event_bus.publish(Event(
    #             topic="fast_path.hubspot",
    #             key=item.source_ref,
    #             value={"source_ref": item.source_ref, ...},
    #         ))

    print("\nSpike ready — needs live Redpanda + Nango connection to execute.")
    print("Run with: docker compose up redpanda && python -m spikes.fast_path_ingest.spike")


if __name__ == "__main__":
    asyncio.run(run_spike())
