"""G11: Extraction cost model.

Must be closed by Week 9, BEFORE design partners ingest real data at scale.

Provides:
1. Per-source extraction cost estimates
2. Budget/depth knob for onboarding
3. Running cost tracking per viewer
4. Alerts when approaching budget limits
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class CostEstimate:
    """Per-source extraction cost estimate."""

    provider_type: str
    items_count: int
    estimated_parse_cost_usd: float
    estimated_extract_cost_usd: float
    estimated_index_cost_usd: float
    total_estimated_usd: float
    notes: str = ""


# Cost per item (rough estimates — calibrated during spike phase)
COST_PER_ITEM_USD: dict[str, dict[str, float]] = {
    "google_sheets": {
        "parse": 0.001,    # Spreadsheet structure detection
        "extract": 0.005,  # LLM extraction per sheet
        "index": 0.0005,   # Qdrant upsert
    },
    "google_drive": {
        "parse": 0.005,    # LlamaParse per document
        "extract": 0.01,   # LLM extraction per document
        "index": 0.001,    # Qdrant upsert
    },
    "gmail": {
        "parse": 0.0005,   # Email parsing (lightweight)
        "extract": 0.002,  # LLM extraction per email
        "index": 0.0005,   # Qdrant upsert
    },
    "hubspot": {
        "parse": 0.0001,   # CRM record parsing (structured)
        "extract": 0.001,  # LLM extraction per record
        "index": 0.0005,   # Qdrant upsert
    },
    "slack": {
        "parse": 0.0005,   # Message parsing
        "extract": 0.002,  # LLM extraction per message
        "index": 0.0005,   # Qdrant upsert
    },
    "gong": {
        "parse": 0.01,     # Transcript parsing (long)
        "extract": 0.05,   # LLM extraction per transcript (expensive)
        "index": 0.002,    # Qdrant upsert
    },
}


def estimate_cost(
    provider_type: str,
    items_count: int,
) -> CostEstimate:
    """Estimate extraction cost for a source."""
    costs = COST_PER_ITEM_USD.get(
        provider_type,
        {"parse": 0.005, "extract": 0.01, "index": 0.001},
    )

    parse_cost = costs["parse"] * items_count
    extract_cost = costs["extract"] * items_count
    index_cost = costs["index"] * items_count
    total = parse_cost + extract_cost + index_cost

    return CostEstimate(
        provider_type=provider_type,
        items_count=items_count,
        estimated_parse_cost_usd=round(parse_cost, 4),
        estimated_extract_cost_usd=round(extract_cost, 4),
        estimated_index_cost_usd=round(index_cost, 4),
        total_estimated_usd=round(total, 4),
    )


def estimate_onboarding_cost(
    sources: list[tuple[str, int]],
) -> tuple[float, list[CostEstimate]]:
    """Estimate total cost for an onboarding session.

    Args:
        sources: List of (provider_type, items_count) tuples

    Returns:
        Total estimated cost and per-source breakdowns
    """
    estimates = [estimate_cost(ptype, count) for ptype, count in sources]
    total = sum(e.total_estimated_usd for e in estimates)
    return round(total, 4), estimates
