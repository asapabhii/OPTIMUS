"""Connector management — real Nango integration."""

from __future__ import annotations

import uuid

import httpx
from fastapi import APIRouter
from pydantic import BaseModel, Field

from libs.config.settings import get_settings
from libs.observability.logging import get_logger

logger = get_logger("connectors")

router = APIRouter()


class ConnectRequest(BaseModel):
    viewer_id: uuid.UUID
    provider_type: str


class ConnectResponse(BaseModel):
    auth_url: str
    connection_id: str
    provider_type: str


class SourceInfo(BaseModel):
    id: str
    provider_type: str
    display_name: str
    connection_id: str
    created_at: str
    is_active: bool = True


class AvailableIntegration(BaseModel):
    provider_type: str
    display_name: str
    description: str
    category: str
    auth_type: str = "oauth2"


# Integrations we support — maps to Nango integration IDs
@router.get("/connectors/available", response_model=list[AvailableIntegration])
async def list_available_integrations() -> list[AvailableIntegration]:
    """Fetch ALL configured integrations dynamically from Nango."""
    settings = get_settings()
    secret = settings.nango_secret_key.get_secret_value()

    if not secret:
        return []

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{settings.nango_base_url}/integrations",
                headers={"Authorization": f"Bearer {secret}"},
                timeout=10.0,
            )
            if resp.status_code != 200:
                logger.warning("nango_list_integrations_failed", status=resp.status_code)
                return []

            body = resp.json()
            configs = body.get("data", []) if isinstance(body, dict) else body

            integrations: list[AvailableIntegration] = []
            for cfg in configs:
                unique_key = cfg.get("unique_key", "")
                provider = cfg.get("provider", unique_key)

                if "getting-started" in unique_key or "getting_started" in unique_key:
                    continue

                display = cfg.get("display_name", unique_key.replace("-", " ").replace("_", " ").title())
                logo = cfg.get("logo", "")

                integrations.append(AvailableIntegration(
                    provider_type=unique_key,
                    display_name=display,
                    description=f"{provider} connector",
                    category="connector",
                    auth_type="oauth2",
                ))

            # Add HubSpot (direct integration, not via Nango)
            hs_exists = any(i.provider_type == "hubspot" for i in integrations)
            if not hs_exists:
                integrations.append(AvailableIntegration(
                    provider_type="hubspot",
                    display_name="HubSpot",
                    description="CRM connector (direct API)",
                    category="crm",
                    auth_type="api_key",
                ))

            return integrations
    except Exception as e:
        logger.error("nango_list_integrations_error", error=str(e))
        return []


@router.get("/connectors/connected")
async def list_connected_sources(viewer_id: uuid.UUID) -> list[SourceInfo]:
    """List real connections from Nango API + HubSpot direct."""
    settings = get_settings()
    secret = settings.nango_secret_key.get_secret_value()
    sources: list[SourceInfo] = []

    # Nango connections
    if secret:
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"{settings.nango_base_url}/connections",
                    headers={"Authorization": f"Bearer {secret}"},
                    timeout=10.0,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    connections = data.get("connections", []) if isinstance(data, dict) else data

                    seen_providers: dict[str, dict] = {}
                    for conn in connections:
                        provider = conn.get("provider_config_key", conn.get("provider", "unknown"))
                        if provider not in seen_providers:
                            seen_providers[provider] = conn

                    for provider, conn in seen_providers.items():
                        sources.append(SourceInfo(
                            id=str(conn.get("id", uuid.uuid4())),
                            provider_type=provider,
                            display_name=provider.replace("-", " ").title(),
                            connection_id=str(conn.get("connection_id", "")),
                            created_at=str(conn.get("created_at", conn.get("created", ""))),
                        ))
                else:
                    logger.warning("nango_list_connections_failed", status=resp.status_code)
        except Exception as e:
            logger.error("nango_list_connections_error", error=str(e))

    # HubSpot direct connection (via Private App token)
    hs_token = settings.hubspot_access_token.get_secret_value()
    if hs_token:
        sources.append(SourceInfo(
            id="hubspot-direct",
            provider_type="hubspot",
            display_name="HubSpot",
            connection_id="hubspot-direct",
            created_at="2026-07-27T00:00:00Z",
        ))

    return sources


@router.post("/connectors/session")
async def create_connect_session(viewer_id: str = "viewer-001") -> dict:
    """Create a Nango Connect session token for the frontend SDK."""
    settings = get_settings()
    secret = settings.nango_secret_key.get_secret_value()

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{settings.nango_base_url}/connect/sessions",
                headers={
                    "Authorization": f"Bearer {secret}",
                    "Content-Type": "application/json",
                },
                json={
                    "end_user": {
                        "id": viewer_id,
                        "display_name": "Optimus User",
                    },
                },
                timeout=10.0,
            )
            if resp.status_code in (200, 201):
                data = resp.json()
                return {"token": data.get("data", {}).get("token", data.get("token", ""))}
            else:
                logger.error("nango_session_failed", status=resp.status_code, body=resp.text[:300])
                return {"error": f"Failed to create session: {resp.text[:200]}", "status": resp.status_code}
    except Exception as e:
        logger.error("nango_session_error", error=str(e))
        return {"error": str(e)}


@router.post("/connectors/connect", response_model=ConnectResponse)
async def connect_source(request: ConnectRequest) -> ConnectResponse:
    settings = get_settings()
    connection_id = f"{request.viewer_id}-{request.provider_type}"

    return ConnectResponse(
        auth_url="",
        connection_id=connection_id,
        provider_type=request.provider_type,
    )


@router.delete("/connectors/{connection_id}")
async def disconnect_source(connection_id: str, provider_config_key: str = "") -> dict[str, str]:
    """Disconnect a source via Nango API or clear HubSpot token."""
    settings = get_settings()

    # Handle HubSpot direct disconnection
    if connection_id == "hubspot-direct" or provider_config_key == "hubspot":
        import os

        # Clear the token from the environment and .env file
        os.environ.pop("HUBSPOT_ACCESS_TOKEN", None)

        # Clear from .env file
        env_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
            ".env",
        )
        if os.path.exists(env_path):
            lines = open(env_path, "r").readlines()
            with open(env_path, "w") as f:
                for line in lines:
                    if not line.startswith("HUBSPOT_ACCESS_TOKEN"):
                        f.write(line)

        # Clear the cached settings
        from functools import lru_cache

        get_settings.cache_clear()
        logger.info("hubspot_disconnected")
        return {"status": "disconnected", "connection_id": "hubspot-direct"}

    # Nango disconnection
    secret = settings.nango_secret_key.get_secret_value()

    try:
        async with httpx.AsyncClient() as client:
            params = {}
            if provider_config_key:
                params["provider_config_key"] = provider_config_key

            resp = await client.delete(
                f"{settings.nango_base_url}/connections/{connection_id}",
                headers={"Authorization": f"Bearer {secret}"},
                params=params,
                timeout=10.0,
            )
            logger.info("nango_disconnect", connection_id=connection_id, status=resp.status_code)
            if resp.status_code not in (200, 204):
                return {"status": "error", "detail": resp.text[:200]}
    except Exception as e:
        logger.error("nango_disconnect_error", error=str(e))
        return {"status": "error", "detail": str(e)}

    return {"status": "disconnected", "connection_id": connection_id}
