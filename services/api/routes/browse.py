"""Browse surface (Surface 2) — entity graph, real data only."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

from services.api.routes.ingest import get_entity_store

router = APIRouter()


class EntitySummary(BaseModel):
    entity_id: str
    name: str
    type: str
    source_count: int
    sources: list[str]
    last_updated: str
    properties: dict[str, Any] | None = None


class EntityGraph(BaseModel):
    entities: list[EntitySummary]
    total: int
    connected_sources: int


@router.get("/browse/entities", response_model=EntityGraph)
async def list_entities(
    viewer_id: str = "",
    entity_type: str | None = None,
    search: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> EntityGraph:
    """List entities from ingested data — scoped to the requesting user."""
    store = get_entity_store(viewer_id=viewer_id)

    filtered = store
    if entity_type:
        filtered = [e for e in filtered if e.type == entity_type]
    if search:
        q = search.lower()
        filtered = [e for e in filtered if q in e.name.lower()]

    sources_set: set[str] = set()
    entities: list[EntitySummary] = []

    for record in filtered:
        sources_set.add(record.source)
        entities.append(EntitySummary(
            entity_id=record.id,
            name=record.name,
            type=record.type,
            source_count=1,
            sources=[record.source],
            last_updated=record.fetched_at,
            properties=record.properties,
        ))

    total = len(entities)
    paginated = entities[offset : offset + limit]

    return EntityGraph(
        entities=paginated,
        total=total,
        connected_sources=len(sources_set),
    )


@router.get("/browse/entities/{entity_id}")
async def get_entity_detail(entity_id: str, viewer_id: str = "") -> dict:
    """Get detail for a specific entity."""
    store = get_entity_store(viewer_id=viewer_id)
    matches = [e for e in store if e.id == entity_id]

    if not matches:
        return {"error": "Entity not found", "entity_id": entity_id}

    entity = matches[0]
    all_from_source = [e for e in store if e.name.lower() == entity.name.lower() and e.type == entity.type]

    return {
        "entity_id": entity.id,
        "name": entity.name,
        "type": entity.type,
        "sources": [
            {
                "source": e.source,
                "source_id": e.source_id,
                "fetched_at": e.fetched_at,
                "properties": e.properties,
            }
            for e in all_from_source
        ],
        "source_count": len({e.source for e in all_from_source}),
    }
