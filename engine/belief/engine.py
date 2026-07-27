"""Belief engine — Build #2: the deepest genuine gap.

A belief is a live computation over whatever evidence the viewer
can currently see (P8). It is NEVER a stored durable truth.

The market actively sells the OPPOSITE of what is required here:
every "AI memory" product stores conclusions durably across sessions
and users — a direct violation of P8/P9.

This engine is the one place where the market has no prior art,
and it is the strongest moat.
"""

from __future__ import annotations

import hashlib
import uuid

from core.models.belief import Belief
from libs.adapters.llm_gateway import LLMGatewayAdapter, LLMRequest
from libs.observability.logging import get_logger
from libs.observability.metrics import belief_recomputations
from core.enums import TaskClass

logger = get_logger("belief_engine")


def compute_evidence_set_hash(evidence_ids: list[uuid.UUID]) -> str:
    """Compute a deterministic hash of the viewer's visible evidence set.

    This is the memoization key. A cache hit is valid ONLY while
    this hash is unchanged. Any change to the viewer's visible
    evidence invalidates the entry.
    """
    sorted_ids = sorted(str(eid) for eid in evidence_ids)
    combined = "|".join(sorted_ids)
    return hashlib.sha256(combined.encode()).hexdigest()


async def derive_belief(
    entity_id: uuid.UUID,
    evidence_ids: list[uuid.UUID],
    evidence_texts: list[str],
    viewer_id: uuid.UUID,
    llm: LLMGatewayAdapter,
) -> Belief:
    """Derive a belief from the viewer's currently-visible evidence.

    THE ANTI-SMUGGLING GUARANTEE: This function takes evidence_ids
    and evidence_texts. It NEVER takes a prior belief value.
    The prior conclusion is structurally unreachable.

    See engine.belief.anti_smuggling for the static verification.
    """
    evidence_set_hash = compute_evidence_set_hash(evidence_ids)

    # Synthesize the belief from evidence alone
    belief_text = await synthesize(
        evidence_texts=evidence_texts,
        entity_id=entity_id,
        llm=llm,
    )

    confidence = compute_confidence(len(evidence_ids), len(evidence_texts))

    belief_recomputations.add(1, {"entity_id": str(entity_id)})

    return Belief(
        entity_id=entity_id,
        belief_text=belief_text,
        evidence_set_hash=evidence_set_hash,
        evidence_ids=evidence_ids,
        confidence=confidence,
        viewer_id=viewer_id,
    )


async def recompute_on_partial_loss(
    entity_id: uuid.UUID,
    surviving_evidence_ids: list[uuid.UUID],
    surviving_evidence_texts: list[str],
    original_evidence_count: int,
    viewer_id: uuid.UUID,
    llm: LLMGatewayAdapter,
) -> Belief | None:
    """Recompute a belief after partial evidence loss (REQ-3.5a).

    When a belief loses access to SOME but not ALL evidence:
    - Recompute from the REMAINING visible evidence
    - Present with REDUCED confidence and updated provenance
    - NEVER reuse the prior conclusion as an input

    Args:
        original_evidence_count: How many evidence items existed BEFORE the loss.
            Must be passed in — we cannot infer how many were lost.

    Returns None if zero evidence remains (evaporation).
    """
    if not surviving_evidence_ids:
        logger.info("belief_evaporated", entity_id=str(entity_id), viewer_id=str(viewer_id))
        return None

    belief = await derive_belief(
        entity_id=entity_id,
        evidence_ids=surviving_evidence_ids,
        evidence_texts=surviving_evidence_texts,
        viewer_id=viewer_id,
        llm=llm,
    )
    belief.recomputed_from_partial = True
    belief.confidence = apply_degradation_factor(
        base_confidence=belief.confidence,
        original_evidence_count=original_evidence_count,
        surviving_evidence_count=len(surviving_evidence_ids),
    )

    logger.info(
        "belief_recomputed_partial",
        entity_id=str(entity_id),
        surviving_count=len(surviving_evidence_ids),
        confidence=belief.confidence,
    )
    return belief


async def synthesize(
    evidence_texts: list[str],
    entity_id: uuid.UUID,
    llm: LLMGatewayAdapter,
) -> str:
    """Synthesize a belief from evidence texts.

    CRITICAL: This function's signature takes evidence_texts and entity_id.
    It does NOT and MUST NOT take any prior_belief, previous_conclusion,
    or similar parameter. This is the anti-smuggling guarantee —
    verified statically by the belief-purity CI suite.
    """
    if not evidence_texts:
        return ""

    prompt = (
        "Based on the following evidence about this entity, "
        "derive a concise conclusion. State only what the evidence supports. "
        "If evidence is limited, say so.\n\n"
        + "\n---\n".join(evidence_texts)
    )

    response = await llm.complete(
        LLMRequest(
            task_class=TaskClass.SYNTHESIS,
            messages=[
                {"role": "system", "content": "You derive conclusions from evidence. Be precise and cite your sources."},
                {"role": "user", "content": prompt},
            ],
        )
    )
    return response.content


def compute_confidence(evidence_count: int, text_count: int) -> float:
    """Compute confidence based on evidence quantity and quality."""
    if evidence_count == 0:
        return 0.0
    base = min(0.5 + (evidence_count * 0.1), 0.95)
    return round(base, 2)


def apply_degradation_factor(
    base_confidence: float,
    original_evidence_count: int,
    surviving_evidence_count: int,
) -> float:
    """Apply degradation factor for partial evidence loss (OD-4).

    Linear in surviving evidence weight — calibrated empirically.
    """
    if original_evidence_count == 0:
        return 0.0
    ratio = surviving_evidence_count / original_evidence_count
    degraded = base_confidence * ratio
    return round(max(degraded, 0.1), 2)
