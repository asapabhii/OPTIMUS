"""Browse surface (Surface 2) — entity graph, real data only."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

from services.api.routes.ingest import get_entity_store

router = APIRouter()

TYPE_PRIORITY = {
    "company": 0,
    "deal": 1,
    "person": 2,
    "spreadsheet": 3,
    "event": 4,
    "channel": 5,
    "document": 6,
    "email": 7,
    "message": 8,
}

MIN_NAME_LENGTH = 2
JUNK_NAMES = {
    "hi", "hello", "test", "untitled", "new doc", "undefined",
    "null", "none", "n/a", "", ".", "..",
}


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
    sort: str = "priority",
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
        filtered = [
            e for e in filtered
            if q in e.name.lower()
            or q in e.source.lower()
            or any(q in str(v).lower() for v in e.properties.values())
        ]

    # Filter out junk/noise entities
    cleaned = []
    for e in filtered:
        name_lower = e.name.lower().strip()
        if len(name_lower) < MIN_NAME_LENGTH:
            continue
        if name_lower in JUNK_NAMES:
            continue
        cleaned.append(e)
    filtered = cleaned

    # Deduplicate by (name, type, source) — merge properties
    seen: dict[tuple[str, str, str], dict] = {}
    for record in filtered:
        key = (record.name.lower().strip(), record.type, record.source)
        if key in seen:
            existing = seen[key]
            for k, v in record.properties.items():
                if v and (k not in existing["props"] or not existing["props"][k]):
                    existing["props"][k] = v
        else:
            seen[key] = {
                "id": record.id,
                "name": record.name,
                "type": record.type,
                "source": record.source,
                "fetched_at": record.fetched_at,
                "props": {**record.properties},
            }

    sources_set: set[str] = set()
    entities: list[EntitySummary] = []

    for item in seen.values():
        sources_set.add(item["source"])
        entities.append(EntitySummary(
            entity_id=item["id"],
            name=item["name"],
            type=item["type"],
            source_count=1,
            sources=[item["source"]],
            last_updated=item["fetched_at"],
            properties=item["props"],
        ))

    # Sort by type priority, then alphabetically
    if sort == "priority":
        entities.sort(
            key=lambda e: (
                TYPE_PRIORITY.get(e.type, 99),
                e.name.lower(),
            )
        )
    elif sort == "name":
        entities.sort(key=lambda e: e.name.lower())
    elif sort == "recent":
        entities.sort(
            key=lambda e: e.last_updated or "",
            reverse=True,
        )
    elif sort == "source":
        entities.sort(key=lambda e: (e.sources[0] if e.sources else "", e.name.lower()))

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
