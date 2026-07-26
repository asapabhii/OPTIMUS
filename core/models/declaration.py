"""Declaration domain model — the G3 bitemporal canon-shaped schema.

SoR declarations and resolution rules made in single-player are stored
here from day one, in canon-shaped bitemporal form, so Gate 5 RATIFIES
rather than re-collects them (G3).

Resolution rules are canon too (REQ-6.4, P17) — promoted, reviewed,
shared through the same propose→approve→ratify path as any fact.
They may carry a scope predicate ("Acme = Acme Inc. IN SALES").
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from core.enums import DeclarationTypeEnum


class Declaration(BaseModel):
    """A system-of-record declaration or resolution rule.

    Bitemporal: valid_from/valid_to is world time (when the declaration is true),
    tx_from/tx_to is system time (when we learned about it).
    """

    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    entity_id: uuid.UUID | None = Field(
        default=None, description="Entity this declaration is about (if applicable)"
    )
    fact_type: str = Field(description="What kind of fact (renewal_date, pricing, etc.)")
    declaration_type: DeclarationTypeEnum
    declared_value: str = Field(description="The declared value or rule text")
    system_of_record_source_id: uuid.UUID | None = Field(
        default=None,
        description="Which source is authoritative for this fact type",
    )

    # Scope predicate for resolution rules (REQ-6.4b)
    scope_predicate: str | None = Field(
        default=None,
        description="Optional scope: 'in sales', 'in legal', etc. "
        "Without this, two teams' same-named entities silently merge.",
    )

    # Bitemporal fields
    valid_from: datetime = Field(default_factory=datetime.utcnow)
    valid_to: datetime | None = Field(
        default=None, description="NULL = currently valid"
    )
    tx_from: datetime = Field(
        default_factory=datetime.utcnow,
        description="When the system learned about this declaration",
    )
    tx_to: datetime | None = Field(
        default=None, description="NULL = current system knowledge"
    )

    # Ownership
    viewer_id: uuid.UUID = Field(description="Who made this declaration — RLS key")
    created_at: datetime = Field(default_factory=datetime.utcnow)
