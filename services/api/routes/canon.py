"""Canon / Company Layer — governed, versioned company knowledge.

The canon is the company's shared source of truth. It holds:
- Assertions: declared facts (e.g., "Acme's contract value is $500K")
- Proposals: suggested changes pending approval
- SoR declarations: which source is authoritative for what
- Audience tags: who can see what

Every assertion has:
- An author and a citation
- A valid time range (bitemporal)
- A status (active, superseded, revoked)
- An audience (who can see it)

No fact enters the canon without human approval. This is P15/P16.
"""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime
from enum import Enum
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from libs.observability.logging import get_logger

logger = get_logger("canon")

router = APIRouter()


# ── Enums ──────────────────────────────────────────────────────────────

class AssertionStatus(str, Enum):
    ACTIVE = "active"
    SUPERSEDED = "superseded"
    REVOKED = "revoked"
    DRAFT = "draft"


class ProposalStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class ProposalSource(str, Enum):
    USER = "user"
    SYSTEM = "system"
    AI_SUGGESTION = "ai_suggestion"
    BYPRODUCT = "byproduct"  # from work layer output


class StakeLevel(str, Enum):
    LOW = "low"        # auto-approve after 24h if no objection
    MEDIUM = "medium"  # single approver
    HIGH = "high"      # requires explicit approval, no auto-promote


# ── Models ─────────────────────────────────────────────────────────────

class Assertion(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    entity_name: str
    entity_type: str  # person, company, deal, etc.
    field: str  # the attribute being asserted
    value: str  # the asserted value
    source: str  # where this came from
    source_type: str = "declaration"  # declaration, sor, ingestion
    author: str  # who created this
    citation: str = ""  # evidence or reference
    status: AssertionStatus = AssertionStatus.ACTIVE
    audience: list[str] = Field(default_factory=lambda: ["all"])
    company_domain: str = ""  # scopes assertion to a company pipeline
    stake_level: StakeLevel = StakeLevel.MEDIUM
    # Bitemporal
    valid_from: str = ""
    valid_to: str = ""  # empty = current
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = ""
    superseded_by: str = ""  # id of the assertion that replaced this
    metadata: dict[str, Any] = {}
    # F-P3: Canon visibility extensions
    ttl_days: int = 0  # 0 = never expires, N = auto-revoke after N days
    promotion_path: str = ""  # "direct" or "proposal" — how it entered canon
    visibility: str = "org"  # "org" (all org), "team" (specific teams), "private"
    tags: list[str] = Field(default_factory=list)  # classification tags


class Proposal(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    # What is being proposed
    action: str  # "create" | "update" | "revoke"
    assertion_id: str = ""  # empty for new assertions
    # Proposed content
    entity_name: str
    entity_type: str
    field: str
    old_value: str = ""
    new_value: str
    source: str
    citation: str = ""
    # Meta
    proposed_by: str
    proposal_source: ProposalSource = ProposalSource.USER
    stake_level: StakeLevel = StakeLevel.MEDIUM
    status: ProposalStatus = ProposalStatus.PENDING
    reason: str = ""  # why this is being proposed
    reviewed_by: str = ""
    reviewed_at: str = ""
    review_note: str = ""
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    audience: list[str] = Field(default_factory=lambda: ["all"])
    company_domain: str = ""  # scopes proposal to a company pipeline


class SoRDeclaration(BaseModel):
    """System of Record declaration — which source is authoritative for what."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    entity_type: str  # "company", "deal", etc.
    field: str  # "contract_value", "renewal_date", etc.
    authoritative_source: str  # "hubspot", "google-sheet", etc.
    declared_by: str
    reason: str = ""
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


# ── In-memory stores (production: Postgres with bitemporal tables) ─────

CANON_FILE = "data/canon.json"
PROPOSALS_FILE = "data/proposals.json"
SOR_FILE = "data/sor_declarations.json"


def _load_json(path: str) -> list[dict]:
    try:
        with open(path, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def _save_json(path: str, data: list[dict]):
    os.makedirs("data", exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


_assertions: list[Assertion] = [Assertion(**a) for a in _load_json(CANON_FILE)]
_proposals: list[Proposal] = [Proposal(**p) for p in _load_json(PROPOSALS_FILE)]
_sor_declarations: list[SoRDeclaration] = [SoRDeclaration(**s) for s in _load_json(SOR_FILE)]


def _persist_assertions():
    _save_json(CANON_FILE, [a.model_dump() for a in _assertions])


def _persist_proposals():
    _save_json(PROPOSALS_FILE, [p.model_dump() for p in _proposals])


def _persist_sor():
    _save_json(SOR_FILE, [s.model_dump() for s in _sor_declarations])


# ── Assertion endpoints ────────────────────────────────────────────────

class CanonOverview(BaseModel):
    assertions: list[Assertion]
    total_assertions: int
    active_count: int
    pending_proposals: int
    sor_declarations: int


@router.get("/canon", response_model=CanonOverview)
async def get_canon_overview(
    entity_type: str = "",
    search: str = "",
    status: str = "",
    company_domain: str = "",
) -> CanonOverview:
    """Get canon — filtered by company domain if provided.

    When a user belongs to a company (detected from work email), they see:
    - Assertions scoped to their domain
    - Assertions with no domain (global)
    """
    filtered = _assertions

    if company_domain:
        filtered = [
            a for a in filtered
            if not a.company_domain or a.company_domain == company_domain
        ]

    if entity_type:
        filtered = [a for a in filtered if a.entity_type == entity_type]
    if status:
        filtered = [a for a in filtered if a.status == status]
    if search:
        q = search.lower()
        filtered = [
            a for a in filtered
            if q in a.entity_name.lower()
            or q in a.field.lower()
            or q in a.value.lower()
        ]

    active = [a for a in _assertions if a.status == AssertionStatus.ACTIVE]
    pending = [p for p in _proposals if p.status == ProposalStatus.PENDING]
    if company_domain:
        pending = [
            p for p in pending
            if not p.company_domain or p.company_domain == company_domain
        ]

    return CanonOverview(
        assertions=filtered,
        total_assertions=len(_assertions),
        active_count=len(active),
        pending_proposals=len(pending),
        sor_declarations=len(_sor_declarations),
    )


class CreateAssertionRequest(BaseModel):
    entity_name: str
    entity_type: str
    field: str
    value: str
    source: str
    citation: str = ""
    author: str = "admin"
    stake_level: StakeLevel = StakeLevel.MEDIUM
    audience: list[str] = ["all"]
    valid_from: str = ""
    valid_to: str = ""


@router.post("/canon/assertions", response_model=Assertion)
async def create_assertion(req: CreateAssertionRequest) -> Assertion:
    """Create a new company assertion directly (bypasses proposal for admin)."""
    assertion = Assertion(
        entity_name=req.entity_name,
        entity_type=req.entity_type,
        field=req.field,
        value=req.value,
        source=req.source,
        source_type="declaration",
        author=req.author,
        citation=req.citation,
        status=AssertionStatus.ACTIVE,
        stake_level=req.stake_level,
        audience=req.audience,
        valid_from=req.valid_from or datetime.utcnow().isoformat(),
    )
    _assertions.append(assertion)
    _persist_assertions()
    logger.info("assertion_created", id=assertion.id, entity=req.entity_name, field=req.field)
    return assertion


@router.put("/canon/assertions/{assertion_id}")
async def update_assertion(assertion_id: str, value: str, author: str = "admin") -> Assertion:
    """Update an assertion — creates a new version, supersedes old."""
    old = next((a for a in _assertions if a.id == assertion_id), None)
    if not old:
        raise HTTPException(404, "Assertion not found")

    # Supersede old
    old.status = AssertionStatus.SUPERSEDED
    old.updated_at = datetime.utcnow().isoformat()

    # Create new version
    new = Assertion(
        entity_name=old.entity_name,
        entity_type=old.entity_type,
        field=old.field,
        value=value,
        source=old.source,
        source_type=old.source_type,
        author=author,
        citation=f"Updated from: {old.value}",
        status=AssertionStatus.ACTIVE,
        stake_level=old.stake_level,
        audience=old.audience,
        valid_from=datetime.utcnow().isoformat(),
    )
    old.superseded_by = new.id
    _assertions.append(new)
    _persist_assertions()
    return new


@router.delete("/canon/assertions/{assertion_id}")
async def revoke_assertion(assertion_id: str, author: str = "admin") -> dict:
    """Revoke an assertion — it remains in history but is no longer active."""
    assertion = next((a for a in _assertions if a.id == assertion_id), None)
    if not assertion:
        raise HTTPException(404, "Assertion not found")

    assertion.status = AssertionStatus.REVOKED
    assertion.updated_at = datetime.utcnow().isoformat()
    assertion.valid_to = datetime.utcnow().isoformat()
    _persist_assertions()
    logger.info("assertion_revoked", id=assertion_id)
    return {"revoked": assertion_id}


# ── Proposal endpoints ─────────────────────────────────────────────────

class CreateProposalRequest(BaseModel):
    action: str = "create"  # create, update, revoke
    assertion_id: str = ""
    entity_name: str
    entity_type: str
    field: str
    new_value: str
    old_value: str = ""
    source: str = ""
    citation: str = ""
    reason: str = ""
    proposed_by: str = "system"
    proposal_source: ProposalSource = ProposalSource.USER
    stake_level: StakeLevel = StakeLevel.MEDIUM


class ProposalQueue(BaseModel):
    proposals: list[Proposal]
    total: int
    pending: int
    approved: int
    rejected: int


@router.get("/canon/proposals", response_model=ProposalQueue)
async def list_proposals(status: str = "") -> ProposalQueue:
    """List all proposals."""
    filtered = _proposals
    if status:
        filtered = [p for p in filtered if p.status == status]

    return ProposalQueue(
        proposals=sorted(filtered, key=lambda p: p.created_at, reverse=True),
        total=len(_proposals),
        pending=sum(1 for p in _proposals if p.status == ProposalStatus.PENDING),
        approved=sum(1 for p in _proposals if p.status == ProposalStatus.APPROVED),
        rejected=sum(1 for p in _proposals if p.status == ProposalStatus.REJECTED),
    )


@router.post("/canon/proposals", response_model=Proposal)
async def create_proposal(req: CreateProposalRequest) -> Proposal:
    """Submit a proposal for review."""
    proposal = Proposal(
        action=req.action,
        assertion_id=req.assertion_id,
        entity_name=req.entity_name,
        entity_type=req.entity_type,
        field=req.field,
        old_value=req.old_value,
        new_value=req.new_value,
        source=req.source,
        citation=req.citation,
        proposed_by=req.proposed_by,
        proposal_source=req.proposal_source,
        stake_level=req.stake_level,
        reason=req.reason,
    )
    _proposals.append(proposal)
    _persist_proposals()
    logger.info("proposal_created", id=proposal.id, action=req.action, entity=req.entity_name)
    return proposal


@router.post("/canon/proposals/{proposal_id}/approve")
async def approve_proposal(
    proposal_id: str, reviewer: str = "admin", note: str = ""
) -> dict:
    """Approve a proposal — creates or updates the canon assertion."""
    proposal = next((p for p in _proposals if p.id == proposal_id), None)
    if not proposal:
        raise HTTPException(404, "Proposal not found")
    if proposal.status != ProposalStatus.PENDING:
        raise HTTPException(400, f"Proposal already {proposal.status}")

    proposal.status = ProposalStatus.APPROVED
    proposal.reviewed_by = reviewer
    proposal.reviewed_at = datetime.utcnow().isoformat()
    proposal.review_note = note

    # Apply the proposal
    if proposal.action == "create":
        assertion = Assertion(
            entity_name=proposal.entity_name,
            entity_type=proposal.entity_type,
            field=proposal.field,
            value=proposal.new_value,
            source=proposal.source,
            source_type="declaration",
            author=proposal.proposed_by,
            citation=proposal.citation,
            status=AssertionStatus.ACTIVE,
            stake_level=proposal.stake_level,
            audience=proposal.audience,
            valid_from=datetime.utcnow().isoformat(),
        )
        _assertions.append(assertion)
    elif proposal.action == "update" and proposal.assertion_id:
        old = next((a for a in _assertions if a.id == proposal.assertion_id), None)
        if old:
            old.status = AssertionStatus.SUPERSEDED
            old.updated_at = datetime.utcnow().isoformat()
            new = Assertion(
                entity_name=proposal.entity_name,
                entity_type=proposal.entity_type,
                field=proposal.field,
                value=proposal.new_value,
                source=proposal.source,
                source_type="declaration",
                author=proposal.proposed_by,
                citation=proposal.citation,
                status=AssertionStatus.ACTIVE,
                stake_level=proposal.stake_level,
                audience=proposal.audience,
                valid_from=datetime.utcnow().isoformat(),
            )
            old.superseded_by = new.id
            _assertions.append(new)
    elif proposal.action == "revoke" and proposal.assertion_id:
        old = next((a for a in _assertions if a.id == proposal.assertion_id), None)
        if old:
            old.status = AssertionStatus.REVOKED
            old.valid_to = datetime.utcnow().isoformat()

    _persist_assertions()
    _persist_proposals()
    logger.info("proposal_approved", id=proposal_id, reviewer=reviewer)
    return {"approved": proposal_id, "action": proposal.action}


@router.post("/canon/proposals/{proposal_id}/reject")
async def reject_proposal(
    proposal_id: str, reviewer: str = "admin", note: str = ""
) -> dict:
    """Reject a proposal."""
    proposal = next((p for p in _proposals if p.id == proposal_id), None)
    if not proposal:
        raise HTTPException(404, "Proposal not found")

    proposal.status = ProposalStatus.REJECTED
    proposal.reviewed_by = reviewer
    proposal.reviewed_at = datetime.utcnow().isoformat()
    proposal.review_note = note
    _persist_proposals()
    logger.info("proposal_rejected", id=proposal_id, reviewer=reviewer)
    return {"rejected": proposal_id}


# ── SoR declarations ──────────────────────────────────────────────────

class CreateSoRRequest(BaseModel):
    entity_type: str
    field: str
    authoritative_source: str
    declared_by: str = "admin"
    reason: str = ""


@router.get("/canon/sor", response_model=list[SoRDeclaration])
async def list_sor_declarations() -> list[SoRDeclaration]:
    return _sor_declarations


@router.post("/canon/sor", response_model=SoRDeclaration)
async def create_sor_declaration(req: CreateSoRRequest) -> SoRDeclaration:
    """Declare which source is authoritative for a field."""
    # Replace existing for same entity_type + field
    global _sor_declarations
    _sor_declarations = [
        s for s in _sor_declarations
        if not (s.entity_type == req.entity_type and s.field == req.field)
    ]

    decl = SoRDeclaration(
        entity_type=req.entity_type,
        field=req.field,
        authoritative_source=req.authoritative_source,
        declared_by=req.declared_by,
        reason=req.reason,
    )
    _sor_declarations.append(decl)
    _persist_sor()
    logger.info("sor_declared", entity_type=req.entity_type, field=req.field, source=req.authoritative_source)
    return decl


@router.delete("/canon/sor/{sor_id}")
async def delete_sor_declaration(sor_id: str) -> dict:
    global _sor_declarations
    _sor_declarations = [s for s in _sor_declarations if s.id != sor_id]
    _persist_sor()
    return {"deleted": sor_id}
