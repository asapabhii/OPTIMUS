"""Long-horizon jobs — Signal -> Decision -> Task -> Interaction loop.

Block 4 W-P4: multi-week autonomous jobs (renewal motions, collections,
onboarding sequences). The system goes dormant and wakes on external signals.

Architecture:
- Signal: external event triggers evaluation
- Decision: deterministic decision table evaluates signal
- Task: dispatched work item (via the Work layer agent)
- Interaction: outbound action (email, Slack message, API call)
- Loop: interaction result re-enters as a new signal

Case state is the knowledge graph. Jobs that mutate a SoR additionally
require write-back (Gate 7) to be live.
"""

from __future__ import annotations

import json
import os
import pathlib
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from libs.observability.logging import get_logger

logger = get_logger("longhorizon")

router = APIRouter()

DATA_DIR = pathlib.Path(__file__).resolve().parents[3] / "data"
JOBS_FILE = str(DATA_DIR / "longhorizon_jobs.json")
SIGNALS_FILE = str(DATA_DIR / "signals.json")


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


# ── Models ─────────────────────────────────────────────────────────────

class JobStatus(str, Enum):
    ACTIVE = "active"
    DORMANT = "dormant"      # waiting for signal
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class SignalType(str, Enum):
    TIMER = "timer"           # scheduled wake-up
    WEBHOOK = "webhook"       # external event
    EMAIL_REPLY = "email_reply"
    DATA_CHANGE = "data_change"
    HUMAN_INPUT = "human_input"
    INTERACTION_RESULT = "interaction_result"


class InteractionChannel(str, Enum):
    EMAIL = "email"
    SLACK = "slack"
    API = "api"
    NONE = "none"


class Signal(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    job_id: str
    type: SignalType
    payload: dict[str, Any] = {}
    received_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    processed: bool = False


class JobStep(BaseModel):
    index: int
    phase: str  # signal | decision | task | interaction
    description: str
    result: dict[str, Any] = {}
    timestamp: str = ""
    status: str = "pending"


class LongHorizonJob(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: str
    # Job definition
    entity_type: str = ""
    entity_id: str = ""
    objective: str
    # Decision rules
    decision_table_id: str = ""
    # Interaction config
    interaction_channel: InteractionChannel = InteractionChannel.NONE
    interaction_template: str = ""
    # State
    status: JobStatus = JobStatus.ACTIVE
    current_phase: str = "signal"  # signal | decision | task | interaction
    iteration: int = 0
    max_iterations: int = 10
    steps: list[JobStep] = []
    # Case state (pointers into the knowledge graph)
    case_state: dict[str, Any] = {}
    # Scheduling
    wake_cron: str = ""  # when to check for signals
    next_wake: str = ""
    # Audit
    viewer_id: str = ""
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    completed_at: str = ""
    error: str = ""


# ── Stores ─────────────────────────────────────────────────────────────

_jobs: list[LongHorizonJob] = [LongHorizonJob(**j) for j in _load_json(JOBS_FILE)]
_signals: list[Signal] = [Signal(**s) for s in _load_json(SIGNALS_FILE)]


def _persist_jobs():
    _save_json(JOBS_FILE, [j.model_dump() for j in _jobs])


def _persist_signals():
    _save_json(SIGNALS_FILE, [s.model_dump() for s in _signals])


# ── Job execution loop ────────────────────────────────────────────────

async def _process_signal(job: LongHorizonJob, signal: Signal) -> dict:
    """Process a signal through the Decision -> Task -> Interaction loop."""

    job.iteration += 1
    job.status = JobStatus.PROCESSING
    result: dict[str, Any] = {"signal": signal.type.value, "iteration": job.iteration}

    # Phase 1: Decision
    job.current_phase = "decision"
    decision_action = "continue"  # default

    if job.decision_table_id:
        try:
            from services.api.routes.processes import _tables
            table = next((t for t in _tables if t.id == job.decision_table_id), None)
            if table:
                entity_data = {**job.case_state, **signal.payload}
                for rule in sorted(table.rules, key=lambda r: r.priority):
                    try:
                        if eval(rule.condition, {"__builtins__": {}}, entity_data):
                            decision_action = rule.action
                            break
                    except Exception:
                        continue
        except Exception:
            pass

    step_decision = JobStep(
        index=len(job.steps) + 1, phase="decision",
        description=f"Decision: {decision_action}",
        result={"action": decision_action, "signal": signal.payload},
        timestamp=datetime.now(timezone.utc).isoformat(),
        status="completed",
    )
    job.steps.append(step_decision)
    result["decision"] = decision_action

    if decision_action in ("complete", "stop", "cancel"):
        job.status = JobStatus.COMPLETED
        job.completed_at = datetime.now(timezone.utc).isoformat()
        _persist_jobs()
        return result

    # Phase 2: Task
    job.current_phase = "task"
    task_output = ""
    try:
        from services.api.routes.work import _run_agent
        prompt = (
            f"Long-horizon job: {job.name}\n"
            f"Objective: {job.objective}\n"
            f"Current iteration: {job.iteration}\n"
            f"Decision: {decision_action}\n"
            f"Signal: {json.dumps(signal.payload)}\n"
            f"Case state: {json.dumps(job.case_state)}\n\n"
            f"Execute the appropriate action for this iteration."
        )
        task_output, steps = await _run_agent(prompt, viewer_id=job.viewer_id, max_iterations=4)
    except Exception as e:
        task_output = f"Task error: {str(e)}"

    step_task = JobStep(
        index=len(job.steps) + 1, phase="task",
        description=f"Task execution (iteration {job.iteration})",
        result={"output": task_output[:1000]},
        timestamp=datetime.now(timezone.utc).isoformat(),
        status="completed",
    )
    job.steps.append(step_task)
    result["task_output"] = task_output[:500]

    # Phase 3: Interaction (if configured)
    job.current_phase = "interaction"
    if job.interaction_channel != InteractionChannel.NONE and job.interaction_template:
        interaction_result = await _send_interaction(job, task_output)
        step_interaction = JobStep(
            index=len(job.steps) + 1, phase="interaction",
            description=f"Interaction via {job.interaction_channel.value}",
            result=interaction_result,
            timestamp=datetime.now(timezone.utc).isoformat(),
            status="completed",
        )
        job.steps.append(step_interaction)
        result["interaction"] = interaction_result

    # Update case state
    job.case_state["last_iteration"] = job.iteration
    job.case_state["last_decision"] = decision_action
    job.case_state["last_output"] = task_output[:500]

    # Check if max iterations reached
    if job.iteration >= job.max_iterations:
        job.status = JobStatus.COMPLETED
        job.completed_at = datetime.now(timezone.utc).isoformat()
    else:
        job.status = JobStatus.DORMANT
        job.current_phase = "signal"

    signal.processed = True
    _persist_jobs()
    _persist_signals()

    return result


async def _send_interaction(job: LongHorizonJob, context: str) -> dict:
    """Send an interaction through the configured channel."""
    message = job.interaction_template
    message = message.replace("{context}", context[:500])
    message = message.replace("{iteration}", str(job.iteration))
    message = message.replace("{job_name}", job.name)

    if job.interaction_channel == InteractionChannel.EMAIL:
        try:
            from services.api.routes.gateway import _send_email
            to = job.case_state.get("contact_email", "")
            if to:
                await _send_email(to, f"Update: {job.name}", message)
                return {"sent": True, "channel": "email", "to": to}
        except Exception as e:
            return {"sent": False, "error": str(e)}

    elif job.interaction_channel == InteractionChannel.SLACK:
        try:
            from services.api.routes.gateway import _slack_send_message
            channel = job.case_state.get("slack_channel", "")
            if channel:
                await _slack_send_message(channel, message)
                return {"sent": True, "channel": "slack", "to": channel}
        except Exception as e:
            return {"sent": False, "error": str(e)}

    return {"sent": False, "reason": "No target configured"}


# ── API Routes ─────────────────────────────────────────────────────────

@router.post("/jobs/create")
async def create_job(
    name: str, description: str, objective: str,
    entity_type: str = "", entity_id: str = "",
    interaction_channel: str = "none",
    interaction_template: str = "",
    decision_table_id: str = "",
    wake_cron: str = "daily",
    max_iterations: int = 10,
    viewer_id: str = "",
) -> dict:
    job = LongHorizonJob(
        name=name, description=description, objective=objective,
        entity_type=entity_type, entity_id=entity_id,
        interaction_channel=InteractionChannel(interaction_channel),
        interaction_template=interaction_template,
        decision_table_id=decision_table_id,
        wake_cron=wake_cron, max_iterations=max_iterations,
        viewer_id=viewer_id,
    )
    _jobs.append(job)
    _persist_jobs()
    return {"job_id": job.id, "status": job.status.value, "name": job.name}


@router.get("/jobs")
async def list_jobs(status: str = "", viewer_id: str = "", limit: int = 20) -> list[dict]:
    jobs = _jobs
    if status:
        jobs = [j for j in jobs if j.status.value == status]
    if viewer_id:
        jobs = [j for j in jobs if j.viewer_id == viewer_id]
    return [
        {
            "id": j.id, "name": j.name, "status": j.status.value,
            "iteration": j.iteration, "max_iterations": j.max_iterations,
            "current_phase": j.current_phase, "created_at": j.created_at,
            "steps": len(j.steps),
        }
        for j in sorted(jobs, key=lambda x: x.created_at, reverse=True)[:limit]
    ]


@router.get("/jobs/{job_id}")
async def get_job(job_id: str) -> dict:
    job = next((j for j in _jobs if j.id == job_id), None)
    if not job:
        raise HTTPException(404, "Job not found")
    return job.model_dump()


@router.post("/jobs/{job_id}/signal")
async def send_signal(job_id: str, signal_type: str = "webhook", payload: dict[str, Any] = {}) -> dict:
    """Send a signal to a dormant job, waking it up."""
    job = next((j for j in _jobs if j.id == job_id), None)
    if not job:
        raise HTTPException(404, "Job not found")

    if job.status not in (JobStatus.ACTIVE, JobStatus.DORMANT):
        raise HTTPException(400, f"Job is {job.status.value}, cannot receive signals")

    signal = Signal(job_id=job_id, type=SignalType(signal_type), payload=payload)
    _signals.append(signal)

    result = await _process_signal(job, signal)
    return {"job_id": job_id, "signal_id": signal.id, "result": result}


@router.post("/jobs/{job_id}/cancel")
async def cancel_job(job_id: str) -> dict:
    job = next((j for j in _jobs if j.id == job_id), None)
    if not job:
        raise HTTPException(404, "Job not found")
    job.status = JobStatus.CANCELLED
    _persist_jobs()
    return {"cancelled": True}


@router.get("/jobs/{job_id}/steps")
async def get_job_steps(job_id: str) -> list[dict]:
    job = next((j for j in _jobs if j.id == job_id), None)
    if not job:
        raise HTTPException(404, "Job not found")
    return [s.model_dump() for s in job.steps]
