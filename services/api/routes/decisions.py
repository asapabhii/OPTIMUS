"""Surface 4: Proposals & Decisions — the decision log.

Gate 3 (thin): every auto-merge and auto-classification visible
and reversible in one place (REQ-8.2 stage 1, REQ-11.2).

Approval must take SECONDS, not minutes (REQ-11.1).
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter
from pydantic import BaseModel, Field

from core.models.decision import AutoDecision

router = APIRouter()


class DecisionListResponse(BaseModel):
    """List of auto-decisions for the decision log."""

    decisions: list[AutoDecision]
    total: int


class RevertRequest(BaseModel):
    """Request to revert an auto-decision."""

    decision_id: uuid.UUID
    reason: str = ""


class RevertResponse(BaseModel):
    """Result of reverting an auto-decision."""

    decision_id: uuid.UUID
    reversed: bool
    message: str


@router.get("/decisions", response_model=DecisionListResponse)
async def list_decisions(
    viewer_id: uuid.UUID,
    decision_type: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> DecisionListResponse:
    """List all auto-decisions — visible and reversible.

    Every auto-merged entity, every freshness classification,
    every auto-applied resolution rule shows up here.

    TODO: Wire to decision_log table with RLS.
    """
    return DecisionListResponse(decisions=[], total=0)


@router.post("/decisions/revert", response_model=RevertResponse)
async def revert_decision(request: RevertRequest) -> RevertResponse:
    """Revert an auto-decision in one click.

    For entity merges: triggers un-merge via Senzing re-resolve.
    For classifications: reverts to the previous classification.

    TODO: Wire to reconciliation engine un-merge and decision log update.
    """
    return RevertResponse(
        decision_id=request.decision_id,
        reversed=True,
        message="Decision reverted",
    )
