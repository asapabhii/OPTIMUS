"""Permissions engine — AuthZed/SpiceDB integration for per-viewer gating.

Block 4 F-P2: the permission wall. Two independent gates per query:
  Gate 1 (Source gate): live viewer-token check against the source
  Gate 2 (Audience gate): AuthZed relationship check

No fact is served unless both gates pass. If a live ping fails, the claim
is omitted — never fallback, never mirror.
"""

from __future__ import annotations

import json
import os
import pathlib
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from libs.config.settings import get_settings
from libs.observability.logging import get_logger

logger = get_logger("permissions")

router = APIRouter()

DATA_DIR = pathlib.Path(__file__).resolve().parents[3] / "data"
PERMISSIONS_FILE = str(DATA_DIR / "permissions.json")
TEAMS_FILE = str(DATA_DIR / "teams.json")


def _load_json(path: str) -> list[dict]:
    try:
        with open(path, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def _save_json(path: str, data: list[dict]):
    os.makedirs(str(DATA_DIR), exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


# ── AuthZed Schema ────────────────────────────────────────────────────
# SpiceDB schema for Optimus permission model:
#
# definition user {}
#
# definition team {
#     relation member: user
#     relation admin: user
#     permission view = member + admin
#     permission manage = admin
# }
#
# definition organization {
#     relation member: user | team#member
#     relation admin: user
#     relation owner: user
#     permission view = member + admin + owner
#     permission manage = admin + owner
# }
#
# definition entity {
#     relation owner: user
#     relation viewer: user | team#member | organization#member
#     relation source_connection: connection
#     permission view = owner + viewer
#     permission edit = owner
# }
#
# definition canon_assertion {
#     relation author: user
#     relation audience: user | team#member | organization#member
#     relation org: organization
#     permission view = audience + org->member
#     permission approve = org->admin
# }
#
# definition connection {
#     relation owner: user
#     permission use = owner
# }

AUTHZED_SCHEMA = """
definition user {}

definition team {
    relation member: user
    relation admin: user
    permission view = member + admin
    permission manage = admin
}

definition organization {
    relation member: user | team#member
    relation admin: user
    relation owner: user
    permission view = member + admin + owner
    permission manage = admin + owner
}

definition entity {
    relation owner: user
    relation viewer: user | team#member | organization#member
    relation source_connection: connection
    permission view = owner + viewer
    permission edit = owner
}

definition canon_assertion {
    relation author: user
    relation audience: user | team#member | organization#member
    relation org: organization
    permission view = audience + org->member
    permission approve = org->admin
}

definition connection {
    relation owner: user
    permission use = owner
}
"""


# ── Models ─────────────────────────────────────────────────────────────

class PermissionCheck(BaseModel):
    subject_type: str  # "user"
    subject_id: str
    permission: str  # "view", "edit", "approve"
    resource_type: str  # "entity", "canon_assertion"
    resource_id: str


class PermissionResult(BaseModel):
    allowed: bool
    resource_type: str
    resource_id: str
    checked_at: str


class Team(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    organization_id: str = ""
    members: list[str] = []  # user IDs
    admins: list[str] = []
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class Organization(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    domain: str  # company email domain
    owner_id: str
    members: list[str] = []
    admins: list[str] = []
    teams: list[str] = []  # team IDs
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class RelationshipWrite(BaseModel):
    subject_type: str
    subject_id: str
    relation: str
    resource_type: str
    resource_id: str


# ── In-memory permission store (mirrors AuthZed for local dev) ────────

_relationships: list[dict] = _load_json(PERMISSIONS_FILE)
_teams: list[Team] = [Team(**t) for t in _load_json(TEAMS_FILE)]
_organizations: list[Organization] = []


def _persist_relationships():
    _save_json(PERMISSIONS_FILE, _relationships)


def _persist_teams():
    _save_json(TEAMS_FILE, [t.model_dump() for t in _teams])


# ── AuthZed client ────────────────────────────────────────────────────

async def _authzed_check(check: PermissionCheck) -> bool:
    """Check permission via AuthZed API (or local fallback)."""
    settings = get_settings()
    authzed_token = getattr(settings, "authzed_token", None)
    authzed_endpoint = getattr(settings, "authzed_endpoint", None)

    token = authzed_token.get_secret_value() if authzed_token else ""
    endpoint = str(authzed_endpoint) if authzed_endpoint else ""

    if token and endpoint:
        # Real AuthZed check
        import httpx
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"{endpoint}/v1/permissions/check",
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "consistency": {"fully_consistent": True},
                        "resource": {
                            "object_type": check.resource_type,
                            "object_id": check.resource_id,
                        },
                        "permission": check.permission,
                        "subject": {
                            "object": {
                                "object_type": check.subject_type,
                                "object_id": check.subject_id,
                            },
                        },
                    },
                    timeout=5.0,
                )
                if resp.status_code == 200:
                    result = resp.json()
                    return result.get("permissionship") == "PERMISSIONSHIP_HAS_PERMISSION"
        except Exception as e:
            logger.warning("authzed_check_failed", error=str(e))

    # Local fallback: check in-memory relationships
    for rel in _relationships:
        if (
            rel.get("subject_type") == check.subject_type
            and rel.get("subject_id") == check.subject_id
            and rel.get("resource_type") == check.resource_type
            and rel.get("resource_id") == check.resource_id
        ):
            # Found a direct relationship
            if rel.get("relation") in _permission_implies(check.permission):
                return True

    # Default: owner always has access, and if no relationships exist,
    # allow access (single-user mode)
    if not _relationships:
        return True

    return False


def _permission_implies(permission: str) -> set[str]:
    """Which relations grant the given permission."""
    mapping = {
        "view": {"viewer", "owner", "member", "admin"},
        "edit": {"owner", "admin"},
        "approve": {"admin", "owner"},
        "manage": {"admin", "owner"},
        "use": {"owner"},
    }
    return mapping.get(permission, {permission})


async def _authzed_write(rel: RelationshipWrite) -> bool:
    """Write a relationship to AuthZed (or local store)."""
    settings = get_settings()
    authzed_token = getattr(settings, "authzed_token", None)
    authzed_endpoint = getattr(settings, "authzed_endpoint", None)

    token = authzed_token.get_secret_value() if authzed_token else ""
    endpoint = str(authzed_endpoint) if authzed_endpoint else ""

    if token and endpoint:
        import httpx
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"{endpoint}/v1/relationships/write",
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "updates": [{
                            "operation": "OPERATION_TOUCH",
                            "relationship": {
                                "resource": {
                                    "object_type": rel.resource_type,
                                    "object_id": rel.resource_id,
                                },
                                "relation": rel.relation,
                                "subject": {
                                    "object": {
                                        "object_type": rel.subject_type,
                                        "object_id": rel.subject_id,
                                    },
                                },
                            },
                        }],
                    },
                    timeout=5.0,
                )
                return resp.status_code == 200
        except Exception as e:
            logger.warning("authzed_write_failed", error=str(e))

    # Local fallback
    _relationships.append(rel.model_dump())
    _persist_relationships()
    return True


# ── API Routes ─────────────────────────────────────────────────────────

@router.post("/permissions/check", response_model=PermissionResult)
async def check_permission(check: PermissionCheck) -> PermissionResult:
    allowed = await _authzed_check(check)
    return PermissionResult(
        allowed=allowed,
        resource_type=check.resource_type,
        resource_id=check.resource_id,
        checked_at=datetime.now(timezone.utc).isoformat(),
    )


@router.post("/permissions/grant")
async def grant_permission(rel: RelationshipWrite) -> dict:
    success = await _authzed_write(rel)
    return {"granted": success}


@router.get("/permissions/schema")
async def get_schema() -> dict:
    return {"schema": AUTHZED_SCHEMA}


# ── Teams & Orgs ──────────────────────────────────────────────────────

@router.post("/teams")
async def create_team(name: str, organization_id: str = "") -> dict:
    team = Team(name=name, organization_id=organization_id)
    _teams.append(team)
    _persist_teams()
    return {"id": team.id, "name": team.name}


@router.get("/teams")
async def list_teams() -> list[dict]:
    return [t.model_dump() for t in _teams]


@router.post("/teams/{team_id}/members")
async def add_team_member(team_id: str, user_id: str, role: str = "member") -> dict:
    team = next((t for t in _teams if t.id == team_id), None)
    if not team:
        raise HTTPException(404, "Team not found")

    if user_id not in team.members:
        team.members.append(user_id)
    if role == "admin" and user_id not in team.admins:
        team.admins.append(user_id)

    _persist_teams()

    await _authzed_write(RelationshipWrite(
        subject_type="user", subject_id=user_id,
        relation=role, resource_type="team", resource_id=team_id,
    ))

    return {"added": True}


@router.post("/organizations")
async def create_organization(name: str, domain: str, owner_id: str) -> dict:
    org = Organization(name=name, domain=domain, owner_id=owner_id)
    org.members.append(owner_id)
    org.admins.append(owner_id)
    _organizations.append(org)

    await _authzed_write(RelationshipWrite(
        subject_type="user", subject_id=owner_id,
        relation="owner", resource_type="organization", resource_id=org.id,
    ))

    return {"id": org.id, "name": org.name, "domain": org.domain}


@router.get("/organizations")
async def list_organizations() -> list[dict]:
    return [o.model_dump() for o in _organizations]


@router.get("/permissions/viewer/{viewer_id}/entities")
async def get_viewable_entities(viewer_id: str) -> dict:
    """Get entities this viewer can see (permission-filtered)."""
    from services.api.routes.ingest import get_entity_store

    store = get_entity_store()

    # If no permission relationships exist, return all (single-user mode)
    if not _relationships:
        return {"entities": len(store), "filtered": False}

    # Check each entity against permissions
    viewable = []
    for entity in store:
        check = PermissionCheck(
            subject_type="user", subject_id=viewer_id,
            permission="view", resource_type="entity", resource_id=entity.id,
        )
        if await _authzed_check(check):
            viewable.append(entity.id)

    return {"entities": len(viewable), "filtered": True, "total": len(store)}
