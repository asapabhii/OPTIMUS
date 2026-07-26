"""Answer envelope model — every answer the system produces carries this.

The answer envelope is the product's differentiating surface (P25, G9).
Four mandatory elements per answer:
1. Per-claim inline citations
2. Per-fact freshness (live-fetched / cached-with-age / immutable)
3. Which layer each fact came from (canon-declared vs personal)
4. Conflicts surfaced, NEVER silently resolved (REQ-8.3)
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class FreshnessInfo(BaseModel):
    """Freshness metadata for a single fact in the answer."""

    status: Literal["live", "cached", "immutable"]
    fetched_at: datetime | None = None
    cache_age_seconds: int | None = None
    source_name: str = ""
    source_ref: str = ""


class Citation(BaseModel):
    """Inline citation for a claim — per claim, not a bibliography (P25)."""

    source_name: str
    source_ref: str
    source_id: uuid.UUID
    snippet: str = ""
    freshness: FreshnessInfo


class ConflictBlock(BaseModel):
    """A surfaced conflict between two sources (REQ-8.3).

    Shows BOTH values, which won, and the rule by which it won.
    Silent arbitration is FORBIDDEN.
    """

    fact_description: str
    value_a: str
    value_a_source: str
    value_a_age: str
    value_b: str
    value_b_source: str
    value_b_age: str
    winner: Literal["a", "b"]
    arbitration_rule: str = Field(
        description="The rule stated in natural language: "
        "'Showing the spreadsheet — it is your declared system of record "
        "for renewals — last edited 2 days ago; the deck\'s figure is 8 months old.'"
    )
    system_of_record_source_id: uuid.UUID | None = None


class Claim(BaseModel):
    """A single claim within an answer, with its citation and freshness."""

    text: str
    citation: Citation
    freshness: FreshnessInfo
    layer: Literal["canon_declared", "personal"] = "personal"
    is_downgraded: bool = Field(
        default=False,
        description="True if this claim could not be verified live. "
        "Shown visibly downgraded, never silently included.",
    )


class PromotionPrompt(BaseModel):
    """At most ONE promotion prompt per answer (P15).

    The conflict the system already detected to answer correctly
    IS the promotion trigger (REQ-6.2). Offered at the moment
    the fact was used, not as a separate chore.
    """

    claim_text: str
    replaces_value: str | None = None
    replaces_age: str | None = None
    evidence_ids: list[uuid.UUID]
    proposed_sor_source_id: uuid.UUID | None = None


class AnswerEnvelope(BaseModel):
    """The complete answer envelope — the product's most important surface."""

    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    question: str
    summary: str = Field(description="Natural language answer")
    claims: list[Claim] = Field(default_factory=list)
    conflicts: list[ConflictBlock] = Field(default_factory=list)
    promotion_prompt: PromotionPrompt | None = Field(
        default=None,
        description="At most one per answer. Stored as a pending proposal.",
    )
    viewer_id: uuid.UUID
    answered_at: datetime = Field(default_factory=datetime.utcnow)
    live_reads_count: int = 0
    cached_reads_count: int = 0
