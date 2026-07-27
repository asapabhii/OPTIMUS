"""Entity domain model — the center of the knowledge graph.

The model is entity-centric (P1): organized around real-world things
(customers, people, SKUs, deals, projects) with sources attached.
Never connector-centric.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from core.enums import VisibilityLevel


class Entity(BaseModel):
    """A thing the organization cares about.

    Structure carries its own visibility level (REQ-3.0c) because
    an entity's NAME can itself be the secret ("Project Nimbus-Acquire").
    """

    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    canonical_name: str
    entity_type: str  # customer, person, product_sku, project, deal
    visibility_level: VisibilityLevel = VisibilityLevel.READABLE
    merged_into: uuid.UUID | None = Field(
        default=None,
        description="If set, this entity was merged into another. "
        "Un-merge triggers resolver record delete/re-resolve.",
    )
    viewer_id: uuid.UUID = Field(description="Owner viewer — RLS partition key")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class EntityLink(BaseModel):
    """Relationship between two entities.

    Part of the structural layer — durable, usually low-sensitivity.
    Survives revocation (REQ-7.4c).
    """

    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    source_entity_id: uuid.UUID
    target_entity_id: uuid.UUID
    relationship_type: str  # belongs_to, related_to, part_of, etc.
    confidence: float = Field(ge=0.0, le=1.0, default=1.0)
    visibility_level: VisibilityLevel = VisibilityLevel.READABLE
    viewer_id: uuid.UUID
    created_at: datetime = Field(default_factory=datetime.utcnow)
