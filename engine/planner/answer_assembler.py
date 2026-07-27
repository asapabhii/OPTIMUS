"""Answer assembler — the final step of the retrieval pipeline.

Every answer carries the four mandatory elements (P25):
1. Per-claim inline citations
2. Per-fact freshness (live / cached / immutable)
3. Which layer each fact came from (canon / personal)
4. Conflicts surfaced with the arbitration rule stated

Plus at most ONE promotion prompt (P15).
"""

from __future__ import annotations

import uuid

from core.enums import TaskClass
from core.models.answer import AnswerEnvelope, ConflictBlock, PromotionPrompt
from engine.planner.planner import FanOutResult
from libs.adapters.llm_gateway import LLMGatewayAdapter, LLMRequest
from libs.observability.logging import get_logger

logger = get_logger("planner.answer_assembler")


async def assemble_answer(
    question: str,
    fan_out_results: list[FanOutResult],
    conflicts: list[ConflictBlock],
    viewer_id: uuid.UUID,
    llm: LLMGatewayAdapter,
) -> AnswerEnvelope:
    """Assemble the final answer envelope from fan-out results.

    Uses the synthesis model tier (P28 — most capable) to produce
    the natural language answer from the gathered evidence.

    The promotion prompt (at most one) is generated here based on
    detected conflicts — the conflict IS the trigger (REQ-6.2).

    TODO: Wire to the full synthesis pipeline.
    """
    # Synthesize the answer using the most capable model
    context_parts: list[str] = []
    for result in fan_out_results:
        for decl in result.declarations:
            context_parts.append(f"Declaration: {decl}")
        for val in result.held_values:
            context_parts.append(f"Held value: {val}")
        for lr in result.live_reads:
            context_parts.append(f"Live read: {lr}")
        for ev in result.evidence:
            context_parts.append(f"Evidence: {ev}")

    context = "\n".join(context_parts) if context_parts else "No evidence available."

    response = await llm.complete(
        LLMRequest(
            task_class=TaskClass.SYNTHESIS,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You synthesize answers from gathered evidence. "
                        "Cite every claim. Note freshness. Surface any conflicts."
                    ),
                },
                {
                    "role": "user",
                    "content": f"Question: {question}\n\nContext:\n{context}",
                },
            ],
        )
    )

    # Build the promotion prompt from the first conflict (at most 1, P15)
    promotion = None
    if conflicts:
        first_conflict = conflicts[0]
        promotion = PromotionPrompt(
            claim_text=first_conflict.fact_description,
            replaces_value=(
                first_conflict.value_b
                if first_conflict.winner == "a"
                else first_conflict.value_a
            ),
            replaces_age=(
                first_conflict.value_b_age
                if first_conflict.winner == "a"
                else first_conflict.value_a_age
            ),
            evidence_ids=[],
            proposed_sor_source_id=first_conflict.system_of_record_source_id,
        )

    live_count = sum(len(r.live_reads) for r in fan_out_results)
    cached_count = sum(len(r.held_values) for r in fan_out_results)

    return AnswerEnvelope(
        question=question,
        summary=response.content,
        conflicts=conflicts,
        promotion_prompt=promotion,
        viewer_id=viewer_id,
        live_reads_count=live_count,
        cached_reads_count=cached_count,
    )
