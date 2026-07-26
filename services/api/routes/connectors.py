"""Connector management — connect/disconnect any source via Nango.

Not limited to a fixed four — works with ANY integration in Nango's catalog.
Specialized overrides exist only where source-specific logic is needed.
"""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

router = APIRouter()


class ConnectRequest(BaseModel):
    """Request to connect a new source."""

    viewer_id: uuid.UUID
    provider_type: str = Field(description="Nango integration type (hubspot, gmail, etc.)")


class ConnectResponse(BaseModel):
    """Response with the Nango OAuth URL to redirect the user to."""

    auth_url: str
    connection_id: str
    provider_type: str


class SourceInfo(BaseModel):
    """Information about a connected source."""

    id: uuid.UUID
    provider_type: str
    display_name: str
    source_class: str
    is_active: bool
    connected_at: str
    items_ingested: int = 0
    entities_found: int = 0


class AvailableIntegration(BaseModel):
    """An available integration from the Nango catalog."""

    provider_type: str
    display_name: str
    description: str
    category: str  # crm, email, documents, communication, project_management
    icon_url: str = ""
    auth_type: str = "oauth2"


@router.get("/connectors/available", response_model=list[AvailableIntegration])
async def list_available_integrations() -> list[AvailableIntegration]:
    """List all available integrations from the Nango catalog.

    Returns the full catalog — the onboarding flow filters
    and bundles based on user intent.

    TODO: Wire to Nango catalog API via CredentialAdapter.
    """
    return []


@router.get("/connectors/connected", response_model=list[SourceInfo])
async def list_connected_sources(viewer_id: uuid.UUID) -> list[SourceInfo]:
    """List all connected sources for a viewer.

    TODO: Wire to sources table with RLS.
    """
    return []


@router.post("/connectors/connect", response_model=ConnectResponse)
async def connect_source(request: ConnectRequest) -> ConnectResponse:
    """Start the OAuth flow to connect a new source.

    The frontend redirects the user to auth_url.
    On callback, Nango manages the token lifecycle.

    TODO: Wire to Nango create_connection + trigger fast-path ingestion.
    """
    return ConnectResponse(
        auth_url="https://api.nango.dev/oauth/connect/...",
        connection_id="pending",
        provider_type=request.provider_type,
    )


@router.delete("/connectors/{source_id}")
async def disconnect_source(source_id: uuid.UUID, viewer_id: uuid.UUID) -> dict[str, str]:
    """Disconnect a source.

    Revokes the Nango connection. Consequences:
    - Live reads for this source will fail (correct — REQ-7.4d)
    - Beliefs depending solely on this source evaporate (REQ-3.5)
    - Beliefs with surviving evidence recompute at reduced confidence (REQ-3.5a)
    - Structure survives, flagged source-unresolvable (REQ-7.4c)

    TODO: Wire to Nango delete_connection + belief recomputation trigger.
    """
    return {"status": "disconnected", "source_id": str(source_id)}
