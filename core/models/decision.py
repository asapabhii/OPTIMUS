"""Auto-decision model — Gate 3: every automatic decision visible and reversible.

The system makes many decisions autonomously (P19): merging entities,
classifying freshness, applying resolution rules. Every one of these
must be observable and reversible (REQ-8.2 stage 1, REQ-11.2).
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from core.enums import AutoDecisionType


class AutoDecision(BaseModel):
    """A decision the system made automatically.

    Visible in the Proposals & Decisions surface (Surface 4).
    Reversible in one click.
    """

    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    decision_type: AutoDecisionType
    input_data: dict = Field(
        default_factory=dict,
        description="What the system was given (e.g., two entity candidates)",
    )
    output_data: dict = Field(
        default_factory=dict,
        description="What the system decided (e.g., merged into entity X)",
    )
    explanation: str = Field(
        default="",
        description="Human-readable explanation. For ER: Splink match breakdown. "
        "For freshness: inference ladder reasoning.",
    )
    confidence: float = Field(
        ge=0.0, le=1.0,
        description="Confidence signal (REQ-8.1a). "
        "Low-confidence decisions should have been escalated.",
    )
    applied_automatically: bool = True
    reversed: bool = False
    reversed_at: datetime | None = None
    reversed_reason: str | None = None
    viewer_id: uuid.UUID
    created_at: datetime = Field(default_factory=datetime.utcnow)
