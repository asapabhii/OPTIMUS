"""Health check endpoints — liveness and readiness probes."""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health() -> dict[str, str]:
    """Liveness probe — is the process running?"""
    return {"status": "ok", "service": "optimus-api"}


@router.get("/ready")
async def ready() -> dict[str, str]:
    """Readiness probe — can the service handle requests?

    TODO: Check database connectivity, Nango reachability, etc.
    """
    return {"status": "ready"}
