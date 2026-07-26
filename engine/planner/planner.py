"""Retrieval planner — Build #5: live-edge detection + 6-way fan-out.

The planner takes a user question and determines:
1. Which entities are relevant (link-set emission)
2. Which edges require live reads (live-edge detection)
3. The parallel fan-out for each entity

The 6-way fan-out (per entity, in parallel):
1. Declaration/canon lookup (bitemporal)
2. Held values with staleness flags
3. Live reads via MCP (viewer's own Nango token)
4. Evidence search (Qdrant, per-viewer collection)
5. Permission pings (batched by principal)
6. Belief memo table (recompute if stale)
"""

from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass, field

from core.enums import TaskClass, VolatilityClass
from core.models.answer import AnswerEnvelope
from libs.adapters.llm_gateway import LLMGatewayAdapter, LLMRequest
from libs.observability.logging import get_logger
from libs.observability.metrics import live_read_latency

logger = get_logger("planner")


@dataclass
class LinkSet:
    """The set of entities and edges relevant to a question."""

    entity_ids: list[uuid.UUID]
    live_edges: list[dict[str, str]] = field(default_factory=list)
    cached_edges: list[dict[str, str]] = field(default_factory=list)


@dataclass
class FanOutResult:
    """Combined result of the 6-way parallel fan-out for one entity."""

    entity_id: uuid.UUID
    declarations: list[dict[str, str]] = field(default_factory=list)
    held_values: list[dict[str, str]] = field(default_factory=list)
    live_reads: list[dict[str, str]] = field(default_factory=list)
    evidence: list[dict[str, str]] = field(default_factory=list)
    permissions: list[dict[str, str]] = field(default_factory=list)
    beliefs: list[dict[str, str]] = field(default_factory=list)


async def plan_retrieval(
    question: str,
    viewer_id: uuid.UUID,
    llm: LLMGatewayAdapter,
) -> LinkSet:
    """Determine the link set for a question.

    Uses the retrieval-planning model tier (P28 — mid-tier)
    to identify relevant entities and classify edge freshness.

    TODO: Wire to entity/declaration store for real entity lookup.
    """
    response = await llm.complete(
        LLMRequest(
            task_class=TaskClass.RETRIEVAL_PLANNING,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a retrieval planner for a knowledge system. "
                        "Given a question, determine which entities and data sources "
                        "are relevant. Return a structured plan."
                    ),
                },
                {"role": "user", "content": question},
            ],
        )
    )

    # TODO: Parse LLM response into LinkSet with real entity IDs
    return LinkSet(entity_ids=[])


async def execute_fan_out(
    entity_id: uuid.UUID,
    viewer_id: uuid.UUID,
    live_edges: list[dict[str, str]],
) -> FanOutResult:
    """Execute the 6-way parallel fan-out for a single entity.

    All six paths execute concurrently. The overall latency
    is the max of the six, not the sum.

    TODO: Wire each path to its respective adapter.
    """
    async def _declarations() -> list[dict[str, str]]:
        # Bitemporal declaration lookup
        return []

    async def _held_values() -> list[dict[str, str]]:
        # Cached values with staleness flags
        return []

    async def _live_reads() -> list[dict[str, str]]:
        # Live reads via MCP/Nango for live-state edges
        return []

    async def _evidence_search() -> list[dict[str, str]]:
        # Qdrant per-viewer evidence search
        return []

    async def _permission_pings() -> list[dict[str, str]]:
        # Batch permission verification by principal
        return []

    async def _belief_lookup() -> list[dict[str, str]]:
        # Belief memo table — recompute if stale
        return []

    results = await asyncio.gather(
        _declarations(),
        _held_values(),
        _live_reads(),
        _evidence_search(),
        _permission_pings(),
        _belief_lookup(),
    )

    return FanOutResult(
        entity_id=entity_id,
        declarations=results[0],
        held_values=results[1],
        live_reads=results[2],
        evidence=results[3],
        permissions=results[4],
        beliefs=results[5],
    )
