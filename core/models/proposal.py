"""Pending proposal model — stored in Phase 1 for the Phase 3 approval queue.

Every answer can produce at most 1 promotion prompt (P15). These are stored
as pending proposals so the Phase 3 approval queue opens ALREADY POPULATED
with weeks of real, work-derived proposals — solving cold start.

Evidence-class sources CANNOT generate proposals (REQ-6.9b, P7).
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from core.enums import SourceClass


class PendingProposal(BaseModel):
    """A claim that qualifies for promotion into the canon.

    Stored in Phase 1; becomes a real approval-queue item at Gate 5.

    The evidence-class bar (REQ-6.9b) is enforced here:
    source_class_of_origin MUST be AUTHORITY, never EVIDENCE.
    """

    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    claim_text: str
    replaces_declaration_id: uuid.UUID | None = None
    replaces_value: str | None = None
    evidence_ids: list[uuid.UUID] = Field(default_factory=list)
    proposed_sor_source_id: uuid.UUID | None = None
    source_class_of_origin: SourceClass = Field(
        description="Must be AUTHORITY — evidence sources cannot generate proposals"
    )
    surfaced_in_answer_id: uuid.UUID | None = None
    viewer_id: uuid.UUID
    created_at: datetime = Field(default_factory=datetime.utcnow)

    @field_validator("source_class_of_origin")
    @classmethod
    def enforce_evidence_class_bar(cls, v: SourceClass) -> SourceClass:
        """REQ-6.9b: evidence-class sources are BARRED from generating proposals.

        A brainstorm thread saying 'maybe drop the enterprise tier' must be
        structurally incapable of conflicting with canonical pricing.
        """
        if v == SourceClass.EVIDENCE:
            msg = (
                "Evidence-class sources cannot generate incremental promotion proposals "
                "(REQ-6.9b). Chat, call, email, and brainstorm content may inform — never assert."
            )
            raise ValueError(msg)
        return v
