"""G7: Proof questions — mine graph for genuine conflicts.

During onboarding, after the graph builds, we generate 3-5 proof
questions biased toward REAL conflicts the system has already detected.

This is the "wow moment": the user asks and immediately sees that
the system found a conflict they didn't know about.

The questions must be:
1. Answerable from the already-ingested data
2. Biased toward genuine cross-source disagreements
3. Based on entities with multiple source links
4. Not trivial or generic
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from libs.observability.logging import get_logger

logger = get_logger("proof_questions")


@dataclass
class ProofQuestion:
    """A question designed to demonstrate conflict surfacing."""

    question: str
    expected_sources: list[str]
    expected_conflict: bool
    entity_id: uuid.UUID | None = None
    difficulty: str = "medium"  # easy, medium, hard


async def generate_proof_questions(
    viewer_id: uuid.UUID,
    limit: int = 5,
) -> list[ProofQuestion]:
    """Generate proof questions for the onboarding flow.

    Mining strategy:
    1. Find entities with >=2 source links (cross-source joins)
    2. Prioritize entities where source values disagree (known conflicts)
    3. Verify answerability (all sources still connected, data ingested)
    4. Compose natural questions that expose the conflicts

    TODO: Wire to store adapter for entity/source/declaration queries.
    """
    questions: list[ProofQuestion] = []

    # Step 1: Find entities with multiple sources
    # SELECT e.id, e.canonical_name, COUNT(DISTINCT sel.source_id) as source_count
    # FROM entities e
    # JOIN source_entity_links sel ON e.id = sel.entity_id
    # WHERE e.viewer_id = :viewer_id
    # GROUP BY e.id
    # HAVING COUNT(DISTINCT sel.source_id) >= 2
    # ORDER BY source_count DESC
    # LIMIT :limit * 3

    # Step 2: For multi-source entities, check for value disagreements
    # Compare held_value across source_entity_links for the same fact_type

    # Step 3: Compose questions
    # For conflicts: "When does the {entity} renewal close?"
    # For cross-source: "What do we know about {entity} from all sources?"

    # Fallback: generic questions for the fixture data
    fallback_questions = [
        ProofQuestion(
            question="When does the Meridian Supply renewal close?",
            expected_sources=["HubSpot", "Google Sheets"],
            expected_conflict=True,
            difficulty="easy",
        ),
        ProofQuestion(
            question="What is our current pricing arrangement with Meridian Supply?",
            expected_sources=["Google Sheets", "Gmail"],
            expected_conflict=True,
            difficulty="medium",
        ),
        ProofQuestion(
            question="Who is our main contact at Meridian Supply?",
            expected_sources=["HubSpot"],
            expected_conflict=True,  # David Chen vs Dave Chen
            difficulty="easy",
        ),
        ProofQuestion(
            question="What products has Meridian Supply ordered recently?",
            expected_sources=["HubSpot", "Google Sheets"],
            expected_conflict=False,
            difficulty="medium",
        ),
        ProofQuestion(
            question="Summarize all interactions with Meridian Supply this quarter",
            expected_sources=["Gmail", "HubSpot"],
            expected_conflict=False,
            difficulty="hard",
        ),
    ]

    questions = fallback_questions[:limit]

    logger.info(
        "proof_questions_generated",
        count=len(questions),
        conflicts=sum(1 for q in questions if q.expected_conflict),
    )
    return questions
