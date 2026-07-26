"""G1: Backfill depth limits and fast-path configuration.

Must exist BEFORE real data ingestion.
Controls how deep the batch backfill goes and how many items
the fast-path lane processes during onboarding.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BackfillConfig:
    """Per-connector backfill configuration."""

    provider_type: str
    fast_path_n: int = 50         # Most-recent N items for onboarding
    backfill_depth_days: int = 365  # How far back to go for full ingestion
    max_items: int | None = None   # Hard cap on total items (cost guard)
    notes: str = ""


# Default backfill policies per provider type
DEFAULT_BACKFILL_CONFIGS: dict[str, BackfillConfig] = {
    "hubspot": BackfillConfig(
        provider_type="hubspot",
        fast_path_n=50,
        backfill_depth_days=365,
        notes="CRM data — full year of deals, contacts, companies",
    ),
    "google_sheets": BackfillConfig(
        provider_type="google_sheets",
        fast_path_n=20,
        backfill_depth_days=365,
        max_items=100,
        notes="Spreadsheets — limited by extraction cost (G11)",
    ),
    "google_drive": BackfillConfig(
        provider_type="google_drive",
        fast_path_n=30,
        backfill_depth_days=180,
        max_items=500,
        notes="Documents — deeper than sheets, parsing cost varies",
    ),
    "gmail": BackfillConfig(
        provider_type="gmail",
        fast_path_n=50,
        backfill_depth_days=90,
        max_items=1000,
        notes="Emails — evidence only, limited depth to control costs",
    ),
    "slack": BackfillConfig(
        provider_type="slack",
        fast_path_n=50,
        backfill_depth_days=90,
        max_items=2000,
        notes="Messages — evidence only, channel-scoped",
    ),
    "gong": BackfillConfig(
        provider_type="gong",
        fast_path_n=20,
        backfill_depth_days=180,
        max_items=200,
        notes="Transcripts — expensive to parse, limited depth",
    ),
}


def get_backfill_config(provider_type: str) -> BackfillConfig:
    """Get the backfill config for a provider type.

    Falls back to generous defaults for unknown providers.
    """
    return DEFAULT_BACKFILL_CONFIGS.get(
        provider_type,
        BackfillConfig(
            provider_type=provider_type,
            fast_path_n=50,
            backfill_depth_days=365,
        ),
    )
