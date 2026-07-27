"""G2 spike: LlamaExtract sheet column-mapping.

THE TEST: Given a spreadsheet, can LlamaExtract correctly infer:
1. Which row is the header?
2. What semantic type is each column? (date, currency, name, ID, etc.)
3. Which column is the entity key? (the column that links rows to entities)

This is the hardest unpriced engineering item. LlamaExtract schemas
absorb most of it — the reason LlamaCloud was chosen over Unstructured.

Success criteria:
  - Header row detected correctly on 5+ test sheets
  - Column types inferred with >= 90% accuracy
  - Entity key column detected on sheets with obvious key columns
  - Works for: renewal trackers, pricing sheets, inventory lists
"""

from __future__ import annotations

import asyncio
import json

# Sample sheet data for testing (the Meridian Supply renewal tracker)
SAMPLE_SHEET = {
    "name": "Renewals Q3 2026",
    "rows": [
        ["Company", "Renewal Date", "Contract Value", "Tier", "Owner", "Notes"],
        ["Meridian Supply", "2026-01-15", "$180,000", "Enterprise", "Sarah Chen", "Multi-year, negotiated pricing"],
        ["Acme Corp", "2026-03-01", "$45,000", "Professional", "James Park", ""],
        ["TechVentures Inc", "2026-04-15", "$92,000", "Enterprise", "Sarah Chen", "Expansion opportunity"],
        ["Global Solutions", "2026-02-28", "$28,000", "Starter", "Mike Brown", "At risk - competitor eval"],
        ["Pacific NW Industries", "2026-05-01", "$156,000", "Enterprise", "James Park", ""],
    ],
}

EXPECTED_SEMANTICS = {
    "header_row": 0,
    "columns": [
        {"name": "Company", "type": "entity_name", "is_entity_key": True},
        {"name": "Renewal Date", "type": "date", "is_entity_key": False},
        {"name": "Contract Value", "type": "currency", "is_entity_key": False},
        {"name": "Tier", "type": "category", "is_entity_key": False},
        {"name": "Owner", "type": "person_name", "is_entity_key": False},
        {"name": "Notes", "type": "free_text", "is_entity_key": False},
    ],
    "entity_key_column": "Company",
}


async def run_spike() -> None:
    """Run the LlamaExtract sheet semantics spike."""

    print(f"Test sheet: {SAMPLE_SHEET['name']}")
    print(f"  Rows: {len(SAMPLE_SHEET['rows'])} (1 header + {len(SAMPLE_SHEET['rows']) - 1} data)")
    print(f"  Columns: {len(SAMPLE_SHEET['rows'][0])}")

    print(f"\nExpected semantics:")
    print(f"  Header row: {EXPECTED_SEMANTICS['header_row']}")
    print(f"  Entity key: {EXPECTED_SEMANTICS['entity_key_column']}")
    for col in EXPECTED_SEMANTICS["columns"]:
        key_marker = " [KEY]" if col["is_entity_key"] else ""
        print(f"    {col['name']}: {col['type']}{key_marker}")

    # TODO: Call LlamaExtract with the sheet data
    # from llama_cloud import LlamaExtract
    #
    # extractor = LlamaExtract(api_key=settings.llama_cloud_api_key)
    # schema = extractor.infer_schema(sheet_data)
    #
    # Compare schema against EXPECTED_SEMANTICS:
    # - header_row match?
    # - column types match?
    # - entity_key_column detected?

    print("\nSpike ready — needs LLAMA_CLOUD_API_KEY to execute.")
    print("Run with: LLAMA_CLOUD_API_KEY=... python -m spikes.llamaextract_sheets.spike")


if __name__ == "__main__":
    asyncio.run(run_spike())
