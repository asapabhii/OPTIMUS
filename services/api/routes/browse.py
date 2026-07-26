"""Surface 2: Browse — the explorable entity graph.

For any entity: every source that mentions it, every belief derived
about it, when each was last refreshed, who can see what.
The debugging surface where power users live.

Includes direct graph manipulation (the promotion escape hatch, REQ-6.10).
"""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

router = APIRouter()


class EntitySummary(BaseModel):
    """Summary of an entity for the graph view."""

    id: uuid.UUID
    canonical_name: str
    entity_type: str
    source_count: int = 0
    belief_count: int = 0
    has_conflicts: bool = False
    last_refreshed: str | None = None


class EntityDetail(BaseModel):
    """Full detail for a single entity — the Browse deep view."""

    entity: EntitySummary
    sources: list[dict[str, Any]] = Field(default_factory=list)
    beliefs: list[dict[str, Any]] = Field(default_factory=list)
    declarations: list[dict[str, Any]] = Field(default_factory=list)
    related_entities: list[EntitySummary] = Field(default_factory=list)


class GraphView(BaseModel):
    """The entity graph for the Browse surface."""

    entities: list[EntitySummary]
    total_count: int
    total_sources: int
    total_beliefs: int
    total_conflicts: int


@router.get("/browse/graph", response_model=GraphView)
async def get_graph(
    viewer_id: uuid.UUID,
    entity_type: str | None = None,
    limit: int = 50,
) -> GraphView:
    """Get the entity graph for the Browse surface.

    TODO: Wire to store adapter with RLS filtering.
    """
    return GraphView(
        entities=[],
        total_count=0,
        total_sources=0,
        total_beliefs=0,
        total_conflicts=0,
    )


@router.get("/browse/entities/{entity_id}", response_model=EntityDetail)
async def get_entity_detail(
    entity_id: uuid.UUID,
    viewer_id: uuid.UUID,
) -> EntityDetail:
    """Get full detail for an entity — sources, beliefs, freshness, declarations.

    TODO: Wire to store with recursive CTE for related entities.
    """
    return EntityDetail(
        entity=EntitySummary(
            id=entity_id,
            canonical_name="[Loading]",
            entity_type="unknown",
        ),
    )
