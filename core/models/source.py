"""Source domain model — connected tools and their links to entities.

Freshness policy attaches to the LINK between an entity and a source,
not to the entity and not to the source (REQ-3.3a).
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from core.enums import CostOfStaleness, SourceClass, VolatilityClass


class Source(BaseModel):
    """An external system the platform connects to.

    Sources split into authorities and evidence (P7).
    Evidence may NEVER assert (REQ-3.2).
    """

    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    nango_connection_id: str = Field(description="Nango-managed connection identifier")
    provider_type: str  # gmail, google_drive, google_sheets, hubspot, slack, gong, etc.
    display_name: str = ""
    source_class: SourceClass = SourceClass.EVIDENCE
    viewer_id: uuid.UUID
    connected_at: datetime = Field(default_factory=datetime.utcnow)
    is_active: bool = True


class SourceEntityLink(BaseModel):
    """The link between an entity and a source — where freshness policy lives.

    This is where the classification axes attach (P5):
    - Volatility: how fast the truth drifts
    - Cost-of-staleness: what breaks if this is wrong

    The link to a live inventory cell is live; the link to a March
    call transcript is immutable. Same entity, different policies (REQ-3.3a).

    The held_value column is NULL when volatility_class is LIVE_STATE —
    enforced by the no_live_values CHECK constraint (REQ-3.3c).
    """

    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    entity_id: uuid.UUID
    source_id: uuid.UUID
    source_ref: str = Field(description="Reference within the source (doc ID, row ID, etc.)")
    volatility_class: VolatilityClass = VolatilityClass.APPEND_ONLY
    cost_of_staleness: CostOfStaleness = CostOfStaleness.MEDIUM
    held_value: str | None = Field(
        default=None,
        description="Cached value for slow-state/frozen facts. "
        "MUST be NULL for live_state (no_live_values constraint).",
    )
    is_stale: bool = False
    version_counter: int = 0
    last_fetched_at: datetime | None = None
    viewer_id: uuid.UUID
    created_at: datetime = Field(default_factory=datetime.utcnow)
