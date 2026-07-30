"""Processes — saved programs, decision tables, judgment nodes.

Block 4 W-P3: the determinism ladder.
- Saved programs: recurring workflows cached as parameterized code
- Decision tables: deterministic branching on entity attributes
- Judgment nodes: LLM calls only at explicitly marked ambiguous steps
- Corrections as patches: expert correction becomes a proposed diff
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

logger = get_logger("processes")

router = APIRouter()

DATA_DIR = pathlib.Path(__file__).resolve().parents[3] / "data"
PROGRAMS_FILE = str(DATA_DIR / "saved_programs.json")
TABLES_FILE = str(DATA_DIR / "decision_tables.json")
RUNS_FILE = str(DATA_DIR / "process_runs.json")


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

class StepType(str, Enum):
    DETERMINISTIC = "deterministic"  # code/rule, no LLM
    JUDGMENT = "judgment"            # LLM call at ambiguous step
    HUMAN = "human"                  # requires human input
    TOOL = "tool"                    # tool call (search, analyze)


class ProcessStep(BaseModel):
    index: int
    name: str
    type: StepType
    action: str  # code template, prompt template, or instruction
    condition: str = ""  # when to execute (empty = always)
    on_low_confidence: str = "escalate"  # escalate | skip | default


class SavedProgram(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: str
    steps: list[ProcessStep]
    parameters: list[str] = []
    category: str = "general"
    author: str = "system"
    version: int = 1
    usage_count: int = 0
    avg_duration_ms: int = 0
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = ""


class DecisionRule(BaseModel):
    condition: str  # Python expression evaluated against entity attributes
    action: str     # what to do when condition is true
    priority: int = 0


class DecisionTable(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: str
    entity_type: str
    rules: list[DecisionRule]
    default_action: str = "skip"
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class ProcessRun(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    program_id: str
    status: str = "running"  # running | completed | failed | paused
    current_step: int = 0
    parameters: dict[str, str] = {}
    step_results: list[dict[str, Any]] = []
    started_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    completed_at: str = ""
    viewer_id: str = ""
    error: str = ""


# ── Stores ─────────────────────────────────────────────────────────────

_programs: list[SavedProgram] = [SavedProgram(**p) for p in _load_json(PROGRAMS_FILE)]
_tables: list[DecisionTable] = [DecisionTable(**t) for t in _load_json(TABLES_FILE)]
_runs: list[ProcessRun] = [ProcessRun(**r) for r in _load_json(RUNS_FILE)]

# Seed example programs if empty
if not _programs:
    _programs = [
        SavedProgram(
            name="Weekly Pipeline Review",
            description="Analyze deal pipeline, flag at-risk deals, generate summary report",
            steps=[
                ProcessStep(index=1, name="Fetch deals", type=StepType.TOOL,
                            action="search_entities(query='', entity_type='deal')"),
                ProcessStep(index=2, name="Analyze pipeline", type=StepType.DETERMINISTIC,
                            action="Group deals by stage, calculate total pipeline value per stage"),
                ProcessStep(index=3, name="Flag at-risk deals", type=StepType.JUDGMENT,
                            action="Review each deal closing within 30 days. Flag if: no recent contact, amount changed, or stage regression."),
                ProcessStep(index=4, name="Generate report", type=StepType.DETERMINISTIC,
                            action="Format findings as a structured pipeline review report with recommendations"),
            ],
            parameters=[],
            category="revenue",
        ),
        SavedProgram(
            name="New Contact Onboarding",
            description="When a new contact is added, enrich data, find related entities, and update Canon",
            steps=[
                ProcessStep(index=1, name="Enrich contact", type=StepType.TOOL,
                            action="search_entities(query='{contact_name}')"),
                ProcessStep(index=2, name="Find company", type=StepType.TOOL,
                            action="search_entities(query='{company_domain}', entity_type='company')"),
                ProcessStep(index=3, name="Check for duplicates", type=StepType.DETERMINISTIC,
                            action="Compare contact against existing entities for potential duplicates"),
                ProcessStep(index=4, name="Propose Canon entry", type=StepType.JUDGMENT,
                            action="If contact is from a new company, propose adding the company to Canon",
                            on_low_confidence="escalate"),
            ],
            parameters=["contact_name", "company_domain"],
            category="data_quality",
        ),
        SavedProgram(
            name="Data Conflict Resolution",
            description="Check for conflicts between sources and propose resolutions",
            steps=[
                ProcessStep(index=1, name="Scan entities", type=StepType.TOOL,
                            action="Find entities that exist in multiple sources"),
                ProcessStep(index=2, name="Compare values", type=StepType.DETERMINISTIC,
                            action="For each multi-source entity, compare field values across sources"),
                ProcessStep(index=3, name="Apply SoR rules", type=StepType.DETERMINISTIC,
                            action="Check Systems of Record declarations to determine authoritative value"),
                ProcessStep(index=4, name="Resolve ambiguous", type=StepType.JUDGMENT,
                            action="For conflicts without a clear SoR, analyze recency and source reliability",
                            on_low_confidence="escalate"),
                ProcessStep(index=5, name="Propose updates", type=StepType.HUMAN,
                            action="Present proposed resolutions for human approval"),
            ],
            parameters=[],
            category="data_quality",
        ),
    ]
    _save_json(PROGRAMS_FILE, [p.model_dump() for p in _programs])

if not _tables:
    _tables = [
        DecisionTable(
            name="Deal Risk Assessment",
            description="Classify deals by risk level based on attributes",
            entity_type="deal",
            rules=[
                DecisionRule(condition="amount > 100000 and stage == 'negotiation'", action="high_value_alert", priority=1),
                DecisionRule(condition="days_since_contact > 14", action="stale_deal_flag", priority=2),
                DecisionRule(condition="stage == 'closed_lost'", action="post_mortem", priority=3),
                DecisionRule(condition="amount > 50000", action="manager_review", priority=4),
            ],
            default_action="standard_pipeline",
        ),
        DecisionTable(
            name="Contact Routing",
            description="Route contacts to appropriate team member based on attributes",
            entity_type="person",
            rules=[
                DecisionRule(condition="'CEO' in job_title or 'VP' in job_title", action="route_executive", priority=1),
                DecisionRule(condition="'engineering' in job_title.lower()", action="route_technical", priority=2),
                DecisionRule(condition="source == 'hubspot'", action="route_sales", priority=3),
            ],
            default_action="route_general",
        ),
    ]
    _save_json(TABLES_FILE, [t.model_dump() for t in _tables])


def _persist_programs():
    _save_json(PROGRAMS_FILE, [p.model_dump() for p in _programs])


def _persist_tables():
    _save_json(TABLES_FILE, [t.model_dump() for t in _tables])


def _persist_runs():
    _save_json(RUNS_FILE, [r.model_dump() for r in _runs])


# ── Program execution ─────────────────────────────────────────────────

async def _execute_program(program: SavedProgram, params: dict, viewer_id: str = "") -> ProcessRun:
    """Execute a saved program step by step."""
    run = ProcessRun(
        program_id=program.id,
        parameters=params,
        viewer_id=viewer_id,
    )
    _runs.append(run)

    try:
        from services.api.routes.work import _run_agent

        for step in program.steps:
            run.current_step = step.index

            # Fill parameters in action template
            action = step.action
            for key, value in params.items():
                action = action.replace(f"{{{key}}}", value)

            if step.type == StepType.HUMAN:
                # Pause for human input
                run.status = "paused"
                run.step_results.append({
                    "step": step.index, "name": step.name,
                    "status": "awaiting_human", "action": action,
                })
                _persist_runs()
                return run

            # Execute via agent
            prompt = f"Step {step.index}: {step.name}\n\nAction: {action}"
            if step.type == StepType.JUDGMENT:
                prompt += "\n\nThis is a judgment step — if you are not confident (< 80%), escalate to the user rather than guessing."

            result_text, steps_taken = await _run_agent(prompt, viewer_id=viewer_id, max_iterations=4)

            run.step_results.append({
                "step": step.index, "name": step.name,
                "type": step.type.value, "output": result_text[:2000],
                "tool_calls": len(steps_taken),
            })

        run.status = "completed"
        run.completed_at = datetime.now(timezone.utc).isoformat()

    except Exception as e:
        run.status = "failed"
        run.error = str(e)
        logger.error("program_execution_failed", program=program.name, error=str(e))

    _persist_runs()
    program.usage_count += 1
    _persist_programs()

    return run


# ── API Routes ─────────────────────────────────────────────────────────

@router.get("/processes/programs")
async def list_programs() -> list[dict]:
    return [p.model_dump() for p in _programs]


@router.get("/processes/programs/{program_id}")
async def get_program(program_id: str) -> dict:
    program = next((p for p in _programs if p.id == program_id), None)
    if not program:
        raise HTTPException(404, "Program not found")
    return program.model_dump()


@router.post("/processes/programs/{program_id}/run")
async def run_program(program_id: str, params: dict[str, str] = {}, viewer_id: str = "") -> dict:
    program = next((p for p in _programs if p.id == program_id), None)
    if not program:
        raise HTTPException(404, "Program not found")

    run = await _execute_program(program, params, viewer_id)
    return {
        "run_id": run.id,
        "status": run.status,
        "steps_completed": len(run.step_results),
        "total_steps": len(program.steps),
        "results": run.step_results,
    }


@router.post("/processes/programs")
async def create_program(
    name: str, description: str, steps: list[dict], parameters: list[str] = [],
    category: str = "general",
) -> dict:
    parsed_steps = [ProcessStep(**s) for s in steps]
    program = SavedProgram(
        name=name, description=description, steps=parsed_steps,
        parameters=parameters, category=category, author="user",
    )
    _programs.append(program)
    _persist_programs()
    return {"id": program.id, "message": f"Program '{name}' created with {len(parsed_steps)} steps"}


@router.post("/processes/programs/{program_id}/patch")
async def patch_program(program_id: str, step_index: int, new_action: str, reason: str = "") -> dict:
    """Apply a correction as a patch to a program step."""
    program = next((p for p in _programs if p.id == program_id), None)
    if not program:
        raise HTTPException(404, "Program not found")

    step = next((s for s in program.steps if s.index == step_index), None)
    if not step:
        raise HTTPException(404, "Step not found")

    old_action = step.action
    step.action = new_action
    program.version += 1
    program.updated_at = datetime.now(timezone.utc).isoformat()
    _persist_programs()

    return {
        "patched": True,
        "step": step_index,
        "old_action": old_action,
        "new_action": new_action,
        "new_version": program.version,
    }


# ── Decision tables ───────────────────────────────────────────────────

@router.get("/processes/tables")
async def list_decision_tables() -> list[dict]:
    return [t.model_dump() for t in _tables]


@router.post("/processes/tables/{table_id}/evaluate")
async def evaluate_decision_table(table_id: str, entity_data: dict[str, Any] = {}) -> dict:
    """Evaluate an entity against a decision table."""
    table = next((t for t in _tables if t.id == table_id), None)
    if not table:
        raise HTTPException(404, "Decision table not found")

    matched_actions = []
    for rule in sorted(table.rules, key=lambda r: r.priority):
        try:
            if eval(rule.condition, {"__builtins__": {}}, entity_data):
                matched_actions.append({"condition": rule.condition, "action": rule.action, "priority": rule.priority})
        except Exception:
            continue

    action = matched_actions[0]["action"] if matched_actions else table.default_action

    return {
        "table": table.name,
        "action": action,
        "matched_rules": len(matched_actions),
        "all_matches": matched_actions,
    }


# ── Run history ───────────────────────────────────────────────────────

@router.get("/processes/runs")
async def list_runs(viewer_id: str = "", limit: int = 20) -> list[dict]:
    runs = _runs
    if viewer_id:
        runs = [r for r in runs if r.viewer_id == viewer_id]
    return [
        {
            "id": r.id,
            "program_id": r.program_id,
            "status": r.status,
            "steps_completed": len(r.step_results),
            "started_at": r.started_at,
            "completed_at": r.completed_at,
        }
        for r in sorted(runs, key=lambda x: x.started_at, reverse=True)[:limit]
    ]
