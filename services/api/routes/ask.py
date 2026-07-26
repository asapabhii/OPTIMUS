"""Surface 1: Ask — the conversational surface.

Every answer carries the full envelope (P25):
- Per-claim inline citations
- Per-fact freshness (live / cached-with-age / immutable)
- Which layer each fact came from
- Conflicts surfaced, NEVER silently resolved
- At most ONE promotion prompt
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from core.models.answer import AnswerEnvelope

router = APIRouter()


class AskRequest(BaseModel):
    """A question from the viewer."""

    question: str = Field(min_length=1, max_length=2000)
    viewer_id: uuid.UUID


class AskResponse(BaseModel):
    """The answer with the full envelope."""

    envelope: AnswerEnvelope


@router.post("/ask", response_model=AskResponse)
async def ask(request: AskRequest) -> AskResponse:
    """Ask a question — the core product interaction.

    Pipeline (Plane B, ~500ms p50 budget):
    1. Retrieval planner determines link set and live edges
    2. Parallel fan-out:
       - Declaration/canon lookup (bitemporal)
       - Held values with staleness flags
       - Live reads via MCP (viewer's own Nango token)
       - Evidence search (Qdrant, per-viewer collection)
       - Permission pings (batched by principal)
       - Belief memo table (recompute if stale)
    3. Conflict detection across sources and layers
    4. Synthesis (Portkey-routed, most-capable model)
    5. Answer envelope assembly
    6. At most 1 promotion prompt (stored as pending proposal)

    TODO: Wire to the retrieval planner and answer assembler.
    """
    envelope = AnswerEnvelope(
        question=request.question,
        summary="[Answer will be assembled by the retrieval planner]",
        viewer_id=request.viewer_id,
    )
    return AskResponse(envelope=envelope)
