"""Declarations — SoR declarations and resolution rules.

Stored canon-shaped and bitemporal from day one (G3),
so Gate 5 RATIFIES rather than re-collects them.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter
from pydantic import BaseModel, Field

from core.enums import DeclarationTypeEnum

router = APIRouter()


class CreateDeclarationRequest(BaseModel):
    """Create a new SoR declaration or resolution rule."""

    viewer_id: uuid.UUID
    entity_id: uuid.UUID | None = None
    fact_type: str
    declaration_type: DeclarationTypeEnum
    declared_value: str
    system_of_record_source_id: uuid.UUID | None = None
    scope_predicate: str | None = Field(
        default=None,
        description="Optional scope for resolution rules: 'in sales', 'in legal'",
    )


class DeclarationResponse(BaseModel):
    """Response for a created declaration."""

    id: uuid.UUID
    fact_type: str
    declaration_type: str
    declared_value: str
    scope_predicate: str | None = None
    created_at: str


@router.post("/declarations", response_model=DeclarationResponse)
async def create_declaration(request: CreateDeclarationRequest) -> DeclarationResponse:
    """Create a new declaration — stored bitemporal from day one.

    Two types:
    - SOR_DECLARATION: "HubSpot is the system of record for deal stage"
    - RESOLUTION_RULE: "Acme = Acme Inc." (may carry scope: "in sales")

    Resolution rules are canon too (REQ-6.4, P17).
    They pre-empt the entity resolver at match time.

    TODO: Wire to store with bitemporal insert.
    """
    return DeclarationResponse(
        id=uuid.uuid4(),
        fact_type=request.fact_type,
        declaration_type=request.declaration_type.value,
        declared_value=request.declared_value,
        scope_predicate=request.scope_predicate,
        created_at="2026-07-26T00:00:00Z",
    )


@router.get("/declarations", response_model=list[DeclarationResponse])
async def list_declarations(
    viewer_id: uuid.UUID,
    declaration_type: str | None = None,
) -> list[DeclarationResponse]:
    """List all declarations for a viewer.

    TODO: Wire to store with RLS + bitemporal query (valid_to IS NULL).
    """
    return []
