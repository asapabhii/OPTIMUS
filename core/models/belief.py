"""Belief domain model — the core of Build #2.

A belief is a DERIVED conclusion — a live computation over whatever
evidence the viewer can currently see (P8). Never a stored durable truth.

Cached only against a hash of the viewer's visible evidence set.
When evidence changes, the belief MUST recompute from surviving evidence
at reduced confidence — NEVER reusing its own prior conclusion (anti-smuggling).
Evaporates only when no visible evidence remains.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class Belief(BaseModel):
    """A derived conclusion about an entity.

    The cache key is (belief_id, evidence_set_hash, viewer_id).
    A cache hit is valid ONLY while the evidence-set hash is unchanged.

    The anti-smuggling guarantee: the recomputation function NEVER
    receives a prior belief value. This is enforced structurally —
    synthesize() takes evidence_ids but no prior_belief parameter.
    """

    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    entity_id: uuid.UUID
    belief_text: str = Field(description="The derived conclusion")
    evidence_set_hash: str = Field(
        description="Hash of the viewer's currently-visible evidence set. "
        "The memoization key. Changes invalidate this belief."
    )
    evidence_ids: list[uuid.UUID] = Field(
        default_factory=list,
        description="The evidence this belief was derived from",
    )
    confidence: float = Field(
        ge=0.0, le=1.0,
        description="Confidence level. Reduced on partial evidence loss (REQ-3.5a).",
    )
    is_stale: bool = Field(
        default=False,
        description="Marked stale when any input evidence changes (REQ-4.4)",
    )
    recomputed_from_partial: bool = Field(
        default=False,
        description="True if this belief was recomputed after partial evidence loss",
    )
    formed_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When this belief was formed — always shown (REQ-4.5)",
    )
    viewer_id: uuid.UUID = Field(description="Per-viewer isolation — RLS partition key")


class BeliefEvaporation(BaseModel):
    """Record of a belief that evaporated — zero visible evidence remains.

    May optionally leave a contentless marker (off until Gate 8 / REQ-5.10).
    """

    belief_id: uuid.UUID
    entity_id: uuid.UUID
    evaporated_at: datetime = Field(default_factory=datetime.utcnow)
    viewer_id: uuid.UUID
    contentless_marker: bool = Field(
        default=False,
        description="If True, viewer is told a prior conclusion existed. "
        "OFF until Gate 8 (discoverability).",
    )
