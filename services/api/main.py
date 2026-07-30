"""Optimus TrustLayer API — Plane B entry point.

The API server is the sync, in-turn path (~500ms p50 budget).
Every request is on behalf of a specific viewer.
Every response carries the answer envelope.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from libs.config.settings import get_settings
from libs.observability.logging import setup_logging, get_logger
from libs.observability.metrics import setup_metrics
from libs.observability.middleware import RequestTracingMiddleware
from libs.observability.tracing import setup_tracing
from services.api.routes import (
    ask, auth, browse, canon, connectors, declarations, decisions,
    gateway, health, ingest, longhorizon, memory, onboarding,
    permissions, processes, work, writeback,
)

logger = get_logger("api")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifecycle — setup and teardown."""
    import asyncio
    settings = get_settings()
    logger.info(
        "starting",
        env=settings.app_env,
        service="optimus-api",
    )

    # Auto-re-ingest if entity store is empty (e.g., after Railway redeploy)
    asyncio.create_task(_auto_reingest_if_empty())

    # Start Slack DM poller (works even without Event Subscriptions)
    asyncio.create_task(_start_slack_poller())

    yield
    logger.info("shutting_down")


async def _auto_reingest_if_empty():
    """If entity store is empty but we have connections, auto-ingest."""
    import asyncio
    await asyncio.sleep(3)  # let the app fully start
    try:
        from services.api.routes.ingest import get_entity_store, ingest_all_connections
        store = get_entity_store()
        if len(store) == 0:
            logger.info("auto_reingest", reason="entity_store_empty_on_startup")
            await ingest_all_connections()
            store = get_entity_store()
            logger.info("auto_reingest_complete", entities=len(store))

        # Also rebuild canon proposals if empty (ephemeral filesystem on Railway)
        await _auto_rebuild_canon_if_empty()
    except Exception as e:
        logger.warning("auto_reingest_failed", error=str(e))


async def _auto_rebuild_canon_if_empty():
    """If canon is empty but entities exist, regenerate proposals from entities."""
    try:
        from services.api.routes.canon import (
            _assertions, _proposals, _persist_proposals,
            Proposal, ProposalSource, StakeLevel,
        )
        from services.api.routes.ingest import get_entity_store

        if len(_assertions) > 0 or len(_proposals) > 0:
            return

        store = get_entity_store()
        if len(store) == 0:
            return

        logger.info("canon_auto_rebuild", reason="canon_empty_but_entities_exist")

        CRM_SOURCES = {"hubspot", "salesforce", "pipedrive"}
        proposals_added = False

        for entity in store:
            if entity.source in CRM_SOURCES:
                if entity.type == "company" and entity.properties.get("domain"):
                    _proposals.append(Proposal(
                        action="create", entity_name=entity.name,
                        entity_type="company", field="domain",
                        new_value=entity.properties["domain"],
                        source=entity.source, proposed_by="system",
                        proposal_source=ProposalSource.SYSTEM,
                        stake_level=StakeLevel.LOW,
                        reason=f"Company from {entity.source} CRM (auto-rebuilt)",
                    ))
                    proposals_added = True
                elif entity.type == "deal" and entity.properties.get("amount"):
                    _proposals.append(Proposal(
                        action="create", entity_name=entity.name,
                        entity_type="deal", field="deal_value",
                        new_value=entity.properties["amount"],
                        source=entity.source, proposed_by="system",
                        proposal_source=ProposalSource.SYSTEM,
                        stake_level=StakeLevel.MEDIUM,
                        reason=f"Deal from {entity.source} CRM (auto-rebuilt)",
                    ))
                    proposals_added = True
                elif entity.type == "person" and entity.properties.get("company"):
                    _proposals.append(Proposal(
                        action="create", entity_name=entity.name,
                        entity_type="person", field="company",
                        new_value=entity.properties["company"],
                        source=entity.source, proposed_by="system",
                        proposal_source=ProposalSource.SYSTEM,
                        stake_level=StakeLevel.LOW,
                        reason=f"Contact from {entity.source} CRM (auto-rebuilt)",
                    ))
                    proposals_added = True

        if proposals_added:
            _persist_proposals()
            logger.info("canon_auto_rebuild_complete", proposals=len(_proposals))
    except Exception as e:
        logger.warning("canon_auto_rebuild_failed", error=str(e))


async def _start_slack_poller():
    """Start the Slack DM poller after a brief delay."""
    import asyncio
    await asyncio.sleep(5)
    try:
        from services.api.routes.gateway import _start_slack_poller as poller
        await poller()
    except Exception as e:
        logger.warning("slack_poller_start_failed", error=str(e))


def create_app() -> FastAPI:
    """Create the FastAPI application."""
    settings = get_settings()

    # Initialize observability BEFORE the app starts
    setup_logging()
    setup_tracing()
    setup_metrics()

    app = FastAPI(
        title="Optimus TrustLayer",
        description=(
            "Knowledge operating system — entity resolution, conflict arbitration, "
            "governed truth. Every answer carries citations, freshness, layer, "
            "and conflicts surfaced with the arbitration rule stated."
        ),
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # Middleware (order matters — outermost first)
    app.add_middleware(RequestTracingMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID", "X-Response-Time-Ms"],
    )

    # Routes — auth (public) + the four surfaces + supporting endpoints
    app.include_router(health.router, tags=["Health"])
    app.include_router(auth.router, prefix="/api/v1", tags=["Auth"])
    app.include_router(ask.router, prefix="/api/v1", tags=["Ask (Surface 1)"])
    app.include_router(browse.router, prefix="/api/v1", tags=["Browse (Surface 2)"])
    app.include_router(decisions.router, prefix="/api/v1", tags=["Decisions (Surface 4)"])
    app.include_router(onboarding.router, prefix="/api/v1", tags=["Onboarding (J1)"])
    app.include_router(connectors.router, prefix="/api/v1", tags=["Connectors"])
    app.include_router(ingest.router, prefix="/api/v1", tags=["Ingestion"])
    app.include_router(declarations.router, prefix="/api/v1", tags=["Declarations"])
    app.include_router(canon.router, prefix="/api/v1", tags=["Canon (Company Layer)"])
    app.include_router(memory.router, prefix="/api/v1", tags=["Memory"])

    # Block 3 — Work Layer
    app.include_router(work.router, prefix="/api/v1", tags=["Work Layer (Block 3)"])

    # Block 4 — Remaining Phases
    app.include_router(permissions.router, prefix="/api/v1", tags=["Permissions (F-P2)"])
    app.include_router(gateway.router, prefix="/api/v1", tags=["Gateway (W-P2)"])
    app.include_router(processes.router, prefix="/api/v1", tags=["Processes (W-P3)"])
    app.include_router(writeback.router, prefix="/api/v1", tags=["Write-back (F-P4)"])
    app.include_router(longhorizon.router, prefix="/api/v1", tags=["Long-horizon Jobs (W-P4)"])

    return app


app = create_app()
