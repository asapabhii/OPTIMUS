"""Provenance model — the record of where a fact came from.

Human authority is a FIRST-CLASS provenance type (REQ-3.2b, P7).
Not all facts trace back to a document. A human-asserted fact carries
who asserted it, in what role, and when.

A belief without provenance is a rumor (REQ-4.5).
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from core.enums import ProvenanceType


class Provenance(BaseModel):
    """How was this fact or belief established?

    Two types:
    - SOURCE_REF: read from a source document/record
    - HUMAN_AUTHORITY: asserted by a human in a specific role
      with its own re-confirmation behavior (REQ-4.6)
    """

    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    provenance_type: ProvenanceType

    # For SOURCE_REF
    source_id: uuid.UUID | None = None
    source_ref: str | None = Field(
        default=None, description="Specific reference within the source"
    )

    # For HUMAN_AUTHORITY (REQ-3.2b)
    human_asserter_id: uuid.UUID | None = None
    human_asserter_role: str | None = Field(
        default=None, description="Role at time of assertion (e.g., 'VP Sales')"
    )
    asserted_at: datetime | None = None

    # Re-validation state (REQ-4.6)
    last_confirmed_at: datetime | None = None
    needs_reconfirmation: bool = False

    created_at: datetime = Field(default_factory=datetime.utcnow)
