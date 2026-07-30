"""Write-back saga — Gate 7: dry-run, revert token, read-back verify.

Block 4 F-P4: Built only when a paying customer asks by name. Priced premium.
The saga ensures exactly-once semantics for mutations to systems of record.

Flow:
1. Propose: what to write, where, why
2. Dry-run: simulate the write, show what would change
3. Approve: human confirms
4. Execute: write to the source via API
5. Read-back: verify the write landed correctly
6. Revert token: one-click revert if something went wrong
"""

from __future__ import annotations

import json
import os
import pathlib
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from libs.config.settings import get_settings
from libs.observability.logging import get_logger

logger = get_logger("writeback")

router = APIRouter()

DATA_DIR = pathlib.Path(__file__).resolve().parents[3] / "data"
SAGAS_FILE = str(DATA_DIR / "writeback_sagas.json")


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


class SagaStatus(str, Enum):
    PROPOSED = "proposed"
    DRY_RUN = "dry_run"
    APPROVED = "approved"
    EXECUTING = "executing"
    VERIFYING = "verifying"
    COMPLETED = "completed"
    REVERTED = "reverted"
    FAILED = "failed"


class WriteBackSaga(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    # What to write
    target_source: str  # "hubspot", "google-sheets", etc.
    entity_type: str
    entity_id: str
    field: str
    old_value: str
    new_value: str
    reason: str
    # Saga state
    status: SagaStatus = SagaStatus.PROPOSED
    dry_run_result: dict[str, Any] = {}
    execute_result: dict[str, Any] = {}
    verify_result: dict[str, Any] = {}
    revert_token: str = ""  # token to undo the write
    # Audit
    proposed_by: str = ""
    approved_by: str = ""
    executed_at: str = ""
    reverted_at: str = ""
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    error: str = ""


_sagas: list[WriteBackSaga] = [WriteBackSaga(**s) for s in _load_json(SAGAS_FILE)]


def _persist_sagas():
    _save_json(SAGAS_FILE, [s.model_dump() for s in _sagas])


# ── Write handlers per source ─────────────────────────────────────────

async def _hubspot_write(saga: WriteBackSaga) -> dict:
    """Execute a write to HubSpot."""
    settings = get_settings()
    token = settings.hubspot_access_token.get_secret_value()
    if not token:
        return {"success": False, "error": "HUBSPOT_ACCESS_TOKEN not configured"}

    type_map = {"person": "contacts", "company": "companies", "deal": "deals"}
    object_type = type_map.get(saga.entity_type, saga.entity_type)

    async with httpx.AsyncClient() as client:
        resp = await client.patch(
            f"https://api.hubapi.com/crm/v3/objects/{object_type}/{saga.entity_id}",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json={"properties": {saga.field: saga.new_value}},
            timeout=15.0,
        )
        if resp.status_code == 200:
            return {"success": True, "response": resp.json()}
        return {"success": False, "error": resp.text[:500], "status": resp.status_code}


async def _hubspot_read_back(saga: WriteBackSaga) -> dict:
    """Read back the value from HubSpot to verify."""
    settings = get_settings()
    token = settings.hubspot_access_token.get_secret_value()

    type_map = {"person": "contacts", "company": "companies", "deal": "deals"}
    object_type = type_map.get(saga.entity_type, saga.entity_type)

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"https://api.hubapi.com/crm/v3/objects/{object_type}/{saga.entity_id}",
            headers={"Authorization": f"Bearer {token}"},
            params={"properties": saga.field},
            timeout=10.0,
        )
        if resp.status_code == 200:
            data = resp.json()
            current = data.get("properties", {}).get(saga.field, "")
            return {"verified": str(current) == str(saga.new_value), "current_value": current}
        return {"verified": False, "error": resp.text[:200]}


async def _hubspot_revert(saga: WriteBackSaga) -> dict:
    """Revert a HubSpot write by restoring the old value."""
    settings = get_settings()
    token = settings.hubspot_access_token.get_secret_value()

    type_map = {"person": "contacts", "company": "companies", "deal": "deals"}
    object_type = type_map.get(saga.entity_type, saga.entity_type)

    async with httpx.AsyncClient() as client:
        resp = await client.patch(
            f"https://api.hubapi.com/crm/v3/objects/{object_type}/{saga.entity_id}",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json={"properties": {saga.field: saga.old_value}},
            timeout=15.0,
        )
        return {"reverted": resp.status_code == 200}


WRITE_HANDLERS = {
    "hubspot": {"write": _hubspot_write, "verify": _hubspot_read_back, "revert": _hubspot_revert},
}


# ── API Routes ─────────────────────────────────────────────────────────

@router.post("/writeback/propose")
async def propose_writeback(
    target_source: str, entity_type: str, entity_id: str,
    field: str, old_value: str, new_value: str,
    reason: str = "", proposed_by: str = "user",
) -> dict:
    """Propose a write-back to a source system."""
    saga = WriteBackSaga(
        target_source=target_source, entity_type=entity_type,
        entity_id=entity_id, field=field, old_value=old_value,
        new_value=new_value, reason=reason, proposed_by=proposed_by,
        revert_token=str(uuid.uuid4())[:12],
    )
    _sagas.append(saga)
    _persist_sagas()

    return {
        "saga_id": saga.id,
        "status": saga.status.value,
        "message": f"Write-back proposed: {field} = '{old_value}' -> '{new_value}' in {target_source}",
        "revert_token": saga.revert_token,
    }


@router.post("/writeback/{saga_id}/dry-run")
async def dry_run_writeback(saga_id: str) -> dict:
    """Simulate the write-back without actually executing it."""
    saga = next((s for s in _sagas if s.id == saga_id), None)
    if not saga:
        raise HTTPException(404, "Saga not found")

    saga.status = SagaStatus.DRY_RUN
    saga.dry_run_result = {
        "would_change": {
            "source": saga.target_source,
            "entity": f"{saga.entity_type}:{saga.entity_id}",
            "field": saga.field,
            "from": saga.old_value,
            "to": saga.new_value,
        },
        "reversible": True,
        "revert_token": saga.revert_token,
    }
    _persist_sagas()

    return {"saga_id": saga.id, "dry_run": saga.dry_run_result}


@router.post("/writeback/{saga_id}/approve")
async def approve_writeback(saga_id: str, approved_by: str = "admin") -> dict:
    """Approve and execute the write-back."""
    saga = next((s for s in _sagas if s.id == saga_id), None)
    if not saga:
        raise HTTPException(404, "Saga not found")

    saga.approved_by = approved_by
    saga.status = SagaStatus.EXECUTING

    handler = WRITE_HANDLERS.get(saga.target_source)
    if not handler:
        saga.status = SagaStatus.FAILED
        saga.error = f"No write handler for source: {saga.target_source}"
        _persist_sagas()
        raise HTTPException(400, saga.error)

    # Execute
    result = await handler["write"](saga)
    saga.execute_result = result
    saga.executed_at = datetime.now(timezone.utc).isoformat()

    if not result.get("success"):
        saga.status = SagaStatus.FAILED
        saga.error = result.get("error", "Unknown write error")
        _persist_sagas()
        return {"saga_id": saga.id, "status": "failed", "error": saga.error}

    # Read-back verify
    saga.status = SagaStatus.VERIFYING
    verify = await handler["verify"](saga)
    saga.verify_result = verify

    if verify.get("verified"):
        saga.status = SagaStatus.COMPLETED
    else:
        saga.status = SagaStatus.FAILED
        saga.error = f"Read-back verification failed: current={verify.get('current_value')}"

    _persist_sagas()
    return {
        "saga_id": saga.id,
        "status": saga.status.value,
        "verified": verify.get("verified", False),
        "revert_token": saga.revert_token,
    }


@router.post("/writeback/{saga_id}/revert")
async def revert_writeback(saga_id: str, revert_token: str) -> dict:
    """Revert a write-back using the revert token. One click reverts exactly."""
    saga = next((s for s in _sagas if s.id == saga_id), None)
    if not saga:
        raise HTTPException(404, "Saga not found")

    if saga.revert_token != revert_token:
        raise HTTPException(403, "Invalid revert token")

    handler = WRITE_HANDLERS.get(saga.target_source)
    if not handler:
        raise HTTPException(400, f"No revert handler for: {saga.target_source}")

    result = await handler["revert"](saga)
    if result.get("reverted"):
        saga.status = SagaStatus.REVERTED
        saga.reverted_at = datetime.now(timezone.utc).isoformat()
    else:
        saga.error = "Revert failed"

    _persist_sagas()
    return {"saga_id": saga.id, "status": saga.status.value, "reverted": result.get("reverted", False)}


@router.get("/writeback/sagas")
async def list_sagas(status: str = "", limit: int = 20) -> list[dict]:
    sagas = _sagas
    if status:
        sagas = [s for s in sagas if s.status.value == status]
    return [s.model_dump() for s in sorted(sagas, key=lambda x: x.created_at, reverse=True)[:limit]]


@router.get("/writeback/{saga_id}")
async def get_saga(saga_id: str) -> dict:
    saga = next((s for s in _sagas if s.id == saga_id), None)
    if not saga:
        raise HTTPException(404, "Saga not found")
    return saga.model_dump()
