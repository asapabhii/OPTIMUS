"""Canon service — Build #4: declarations, resolution rules, proposals.

Declarations stored bitemporal from day one (G3).
Resolution rules as canon with scope predicates (REQ-6.4).
At most 1 promotion prompt per answer (P15).
Evidence-class bar enforced (REQ-6.9b).
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from core.enums import DeclarationTypeEnum, SourceClass
from core.models.declaration import Declaration
from core.models.proposal import PendingProposal
from libs.observability.logging import get_logger

logger = get_logger("canon.declarations")


async def create_declaration(
    viewer_id: uuid.UUID,
    fact_type: str,
    declaration_type: DeclarationTypeEnum,
    declared_value: str,
    entity_id: uuid.UUID | None = None,
    system_of_record_source_id: uuid.UUID | None = None,
    scope_predicate: str | None = None,
) -> Declaration:
    """Create a new declaration — stored bitemporal.

    Two types:
    - SOR_DECLARATION: "HubSpot is the SoR for deal stage"
    - RESOLUTION_RULE: "Acme = Acme Inc." with optional scope

    TODO: Wire to declarations table via store adapter.
    """
    now = datetime.now(timezone.utc)

    declaration = Declaration(
        entity_id=entity_id,
        fact_type=fact_type,
        declaration_type=declaration_type,
        declared_value=declared_value,
        system_of_record_source_id=system_of_record_source_id,
        scope_predicate=scope_predicate,
        valid_from=now,
        tx_from=now,
        viewer_id=viewer_id,
    )

    logger.info(
        "declaration_created",
        type=declaration_type.value,
        fact_type=fact_type,
        viewer_id=str(viewer_id),
    )
    return declaration


async def create_proposal(
    claim_text: str,
    evidence_ids: list[uuid.UUID],
    source_class_of_origin: SourceClass,
    viewer_id: uuid.UUID,
    proposed_sor_source_id: uuid.UUID | None = None,
    replaces_declaration_id: uuid.UUID | None = None,
    replaces_value: str | None = None,
    surfaced_in_answer_id: uuid.UUID | None = None,
) -> PendingProposal:
    """Create a pending proposal — stored in Phase 1, activated at Gate 5.

    Enforces the evidence-class bar at creation time (REQ-6.9b).
    The Pydantic validator will reject proposals from evidence sources.
    """
    proposal = PendingProposal(
        claim_text=claim_text,
        evidence_ids=evidence_ids,
        source_class_of_origin=source_class_of_origin,
        viewer_id=viewer_id,
        proposed_sor_source_id=proposed_sor_source_id,
        replaces_declaration_id=replaces_declaration_id,
        replaces_value=replaces_value,
        surfaced_in_answer_id=surfaced_in_answer_id,
    )

    logger.info(
        "proposal_created",
        claim=claim_text[:100],
        source_class=source_class_of_origin.value,
        viewer_id=str(viewer_id),
    )
    return proposal
