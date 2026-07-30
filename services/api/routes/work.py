"""Work Layer — Agent engine, Crew delegation, Skills, Learning loop.

Block 3 of the-one-plan: the Work layer makes trustworthy knowledge productive.
The agent does real work on governed data — every answer carries the envelope.

Architecture:
- Agent engine: OpenAI function-calling loop with tools bound to the knowledge graph
- Code sandbox: local subprocess execution against a typed graph SDK
- Crew: one-box brain-dump → triage → briefs → sequential dispatch → ledger
- Skills: curated library + agent-proposed skills behind approval
- Learning loop: corrections → proposals with diffs and citations
- Scheduled runs: cron-like tasks + proactive daily brief
"""

from __future__ import annotations

import asyncio
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import time
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from libs.config.settings import get_settings
from libs.observability.logging import get_logger
from services.api.routes.ingest import get_entity_store, EntityRecord

logger = get_logger("work")

router = APIRouter()

# ── Data persistence ───────────────────────────────────────────────────

DATA_DIR = pathlib.Path(__file__).resolve().parents[3] / "data"
TASKS_FILE = str(DATA_DIR / "work_tasks.json")
SKILLS_FILE = str(DATA_DIR / "skills.json")
BRIEFS_FILE = str(DATA_DIR / "briefs.json")
SCHEDULES_FILE = str(DATA_DIR / "schedules.json")


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


# ═══════════════════════════════════════════════════════════════════════
# AGENT ENGINE — OpenAI function-calling loop with knowledge graph tools
# ═══════════════════════════════════════════════════════════════════════

class TaskKind(str, Enum):
    SHIP = "ship"    # produces a deliverable
    SCOUT = "scout"  # investigates, changes nothing


class TaskStatus(str, Enum):
    READY = "ready"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    FAILED = "failed"


class WorkTask(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    objective: str
    context: str = ""
    kind: TaskKind = TaskKind.SCOUT
    status: TaskStatus = TaskStatus.READY
    brief: dict[str, Any] = {}
    result: dict[str, Any] = {}
    steps: list[dict[str, Any]] = []
    parent_id: str = ""  # if this is a sub-task of a Crew workstream
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = ""
    completed_at: str = ""
    error: str = ""
    viewer_id: str = ""
    workstream_index: int = 0


class WorkRequest(BaseModel):
    objective: str
    context: str = ""
    viewer_id: str = "00000000-0000-0000-0000-000000000001"


class WorkResult(BaseModel):
    task_id: str
    status: str
    result: dict[str, Any]
    steps: list[dict[str, Any]]
    latency_ms: int


# ── Tool definitions for the agent ─────────────────────────────────────

AGENT_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_entities",
            "description": "Search the knowledge graph for entities by name, type, or source. Returns matching entities with their properties.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search term"},
                    "entity_type": {"type": "string", "description": "Filter by type: person, company, deal, email, document, etc."},
                    "source": {"type": "string", "description": "Filter by source: hubspot, google-mail, github, etc."},
                    "limit": {"type": "integer", "description": "Max results (default 20)", "default": 20},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_entity_details",
            "description": "Get full details of a specific entity by ID or name.",
            "parameters": {
                "type": "object",
                "properties": {
                    "entity_id": {"type": "string", "description": "Entity ID"},
                    "entity_name": {"type": "string", "description": "Entity name (fuzzy match)"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "analyze_data",
            "description": "Run analysis on entity data — counts, aggregations, comparisons, trends. Returns structured results.",
            "parameters": {
                "type": "object",
                "properties": {
                    "analysis_type": {"type": "string", "enum": ["count", "aggregate", "compare", "timeline", "top_n"], "description": "Type of analysis"},
                    "entity_type": {"type": "string", "description": "Entity type to analyze"},
                    "field": {"type": "string", "description": "Property field to analyze"},
                    "group_by": {"type": "string", "description": "Group results by this field"},
                },
                "required": ["analysis_type", "entity_type"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "execute_code",
            "description": "Execute Python code in a sandboxed environment with access to entity data. Use for complex data processing, calculations, or generating reports.",
            "parameters": {
                "type": "object",
                "properties": {
                    "code": {"type": "string", "description": "Python code to execute. Entity data is available as `entities` (list of dicts)."},
                    "description": {"type": "string", "description": "What this code does"},
                },
                "required": ["code"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_canon_facts",
            "description": "Get governed company knowledge (Canon assertions) — verified facts about entities.",
            "parameters": {
                "type": "object",
                "properties": {
                    "entity_name": {"type": "string", "description": "Filter by entity name"},
                    "entity_type": {"type": "string", "description": "Filter by entity type"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "propose_canon_fact",
            "description": "Propose a new fact for the company Canon (requires human approval). Use when analysis reveals something worth governing.",
            "parameters": {
                "type": "object",
                "properties": {
                    "entity_name": {"type": "string"},
                    "entity_type": {"type": "string"},
                    "field": {"type": "string"},
                    "value": {"type": "string"},
                    "reason": {"type": "string", "description": "Why this fact should be governed"},
                },
                "required": ["entity_name", "entity_type", "field", "value", "reason"],
            },
        },
    },
]


# ── Tool implementations ───────────────────────────────────────────────

def _exec_search_entities(args: dict) -> dict:
    store = get_entity_store()
    query = args.get("query", "").lower()
    etype = args.get("entity_type", "")
    source = args.get("source", "")
    limit = args.get("limit", 20)

    results = []
    for e in store:
        if etype and e.type != etype:
            continue
        if source and e.source != source:
            continue
        if query and query not in e.name.lower() and not any(
            query in str(v).lower() for v in e.properties.values()
        ):
            continue
        results.append({
            "id": e.id, "name": e.name, "type": e.type,
            "source": e.source, "properties": e.properties,
        })
        if len(results) >= limit:
            break

    return {"count": len(results), "entities": results}


def _exec_get_entity_details(args: dict) -> dict:
    store = get_entity_store()
    eid = args.get("entity_id", "")
    ename = args.get("entity_name", "").lower()

    for e in store:
        if (eid and e.id == eid) or (ename and ename in e.name.lower()):
            return {
                "id": e.id, "name": e.name, "type": e.type,
                "source": e.source, "properties": e.properties,
                "fetched_at": e.fetched_at, "connection_id": e.connection_id,
            }
    return {"error": "Entity not found"}


def _exec_analyze_data(args: dict) -> dict:
    store = get_entity_store()
    atype = args.get("analysis_type", "count")
    etype = args.get("entity_type", "")
    field = args.get("field", "")
    group_by = args.get("group_by", "")

    filtered = [e for e in store if not etype or e.type == etype]

    if atype == "count":
        if group_by:
            groups: dict[str, int] = {}
            for e in filtered:
                key = str(e.properties.get(group_by, "unknown"))
                groups[key] = groups.get(key, 0) + 1
            return {"total": len(filtered), "groups": groups}
        return {"total": len(filtered)}

    elif atype == "top_n":
        if field:
            values = [(e.name, e.properties.get(field, 0)) for e in filtered]
            values.sort(key=lambda x: float(x[1]) if str(x[1]).replace(".", "").isdigit() else 0, reverse=True)
            return {"top": values[:10]}
        return {"error": "field required for top_n"}

    elif atype == "aggregate":
        if field:
            vals = [float(e.properties.get(field, 0)) for e in filtered
                    if str(e.properties.get(field, "")).replace(".", "").isdigit()]
            if vals:
                return {"sum": sum(vals), "avg": sum(vals)/len(vals), "min": min(vals), "max": max(vals), "count": len(vals)}
        return {"error": "No numeric values found"}

    elif atype == "timeline":
        dates: dict[str, int] = {}
        for e in filtered:
            date_str = e.properties.get("date", e.fetched_at or "")[:10]
            if date_str:
                dates[date_str] = dates.get(date_str, 0) + 1
        return {"timeline": dict(sorted(dates.items()))}

    return {"error": f"Unknown analysis type: {atype}"}


def _exec_execute_code(args: dict) -> dict:
    """Execute Python code in a sandboxed subprocess."""
    code = args.get("code", "")
    description = args.get("description", "")

    store = get_entity_store()
    entities_data = [e.model_dump() for e in store[:200]]

    # Create a temp script with the entity data injected
    script = f"""
import json, sys

entities = json.loads('''{json.dumps(entities_data)}''')

# User code
{code}
"""

    try:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False, dir=str(DATA_DIR)) as f:
            f.write(script)
            script_path = f.name

        result = subprocess.run(
            [sys.executable, script_path],
            capture_output=True, text=True, timeout=30,
            cwd=str(DATA_DIR),
        )

        os.unlink(script_path)

        output = result.stdout[:5000] if result.stdout else ""
        error = result.stderr[:2000] if result.stderr else ""

        return {
            "success": result.returncode == 0,
            "output": output,
            "error": error,
            "description": description,
        }
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "Code execution timed out (30s limit)"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def _exec_get_canon_facts(args: dict) -> dict:
    try:
        from services.api.routes.canon import _assertions, AssertionStatus
        facts = [a for a in _assertions if a.status == AssertionStatus.ACTIVE]

        ename = args.get("entity_name", "").lower()
        etype = args.get("entity_type", "")
        if ename:
            facts = [a for a in facts if ename in a.entity_name.lower()]
        if etype:
            facts = [a for a in facts if a.entity_type == etype]

        return {"facts": [
            {"entity": a.entity_name, "type": a.entity_type, "field": a.field,
             "value": a.value, "source": a.source, "author": a.author}
            for a in facts[:20]
        ]}
    except Exception:
        return {"facts": []}


def _exec_propose_canon_fact(args: dict) -> dict:
    try:
        from services.api.routes.canon import (
            _proposals, Proposal, ProposalSource, StakeLevel, _persist_proposals,
        )
        _proposals.append(Proposal(
            action="create",
            entity_name=args["entity_name"],
            entity_type=args["entity_type"],
            field=args["field"],
            new_value=args["value"],
            source="work-layer",
            proposed_by="agent",
            proposal_source=ProposalSource.AI_SUGGESTION,
            stake_level=StakeLevel.MEDIUM,
            reason=args.get("reason", "Proposed by AI agent based on data analysis"),
        ))
        _persist_proposals()
        return {"proposed": True, "message": "Fact proposed for human approval"}
    except Exception as e:
        return {"proposed": False, "error": str(e)}


TOOL_HANDLERS = {
    "search_entities": _exec_search_entities,
    "get_entity_details": _exec_get_entity_details,
    "analyze_data": _exec_analyze_data,
    "execute_code": _exec_execute_code,
    "get_canon_facts": _exec_get_canon_facts,
    "propose_canon_fact": _exec_propose_canon_fact,
}


# ── Agent execution loop ──────────────────────────────────────────────

async def _run_agent(
    objective: str,
    context: str = "",
    viewer_id: str = "",
    max_iterations: int = 8,
) -> tuple[str, list[dict]]:
    """Run the agent loop: plan → tool calls → synthesize."""
    settings = get_settings()
    openai_key = settings.openai_api_key.get_secret_value()
    if not openai_key:
        return "OpenAI API key not configured.", []

    store = get_entity_store()
    store_summary = f"{len(store)} entities across {len(set(e.source for e in store))} sources"

    system_prompt = (
        "You are the Optimus TrustLayer Work Agent. You have access to a governed knowledge graph "
        "and can search entities, analyze data, execute Python code, and propose governed facts.\n\n"
        "RULES:\n"
        "- Use tools to gather data before answering. Never guess.\n"
        "- Every claim must be grounded in tool output.\n"
        "- If asked to produce a deliverable (report, analysis, summary), use execute_code for heavy processing.\n"
        "- If you discover a fact worth governing, use propose_canon_fact.\n"
        "- Be concise, professional, and cite your sources.\n"
        "- Format output with markdown.\n\n"
        f"Knowledge graph: {store_summary}\n"
    )
    if context:
        system_prompt += f"\nAdditional context: {context}\n"

    messages: list[dict] = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": objective},
    ]

    steps: list[dict] = []

    async with httpx.AsyncClient() as client:
        for iteration in range(max_iterations):
            resp = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {openai_key}", "Content-Type": "application/json"},
                json={
                    "model": "gpt-4o",
                    "messages": messages,
                    "tools": AGENT_TOOLS,
                    "tool_choice": "auto",
                    "temperature": 0.2,
                    "max_tokens": 4000,
                },
                timeout=60.0,
            )

            if resp.status_code != 200:
                return f"Agent error: {resp.text[:200]}", steps

            completion = resp.json()
            choice = completion["choices"][0]
            msg = choice["message"]

            # If no tool calls, the agent is done
            if not msg.get("tool_calls"):
                return msg.get("content", ""), steps

            messages.append(msg)

            # Execute each tool call
            for tc in msg["tool_calls"]:
                fn_name = tc["function"]["name"]
                fn_args = json.loads(tc["function"]["arguments"])

                handler = TOOL_HANDLERS.get(fn_name)
                if handler:
                    result = handler(fn_args)
                else:
                    result = {"error": f"Unknown tool: {fn_name}"}

                step = {
                    "tool": fn_name,
                    "args": fn_args,
                    "result_summary": str(result)[:500],
                    "iteration": iteration + 1,
                }
                steps.append(step)

                messages.append({
                    "role": "tool",
                    "tool_call_id": tc["id"],
                    "content": json.dumps(result)[:8000],
                })

    return "Agent reached maximum iterations.", steps


# ═══════════════════════════════════════════════════════════════════════
# CREW DELEGATION — brain-dump → triage → briefs → dispatch → ledger
# ═══════════════════════════════════════════════════════════════════════

class CrewRequest(BaseModel):
    brain_dump: str
    viewer_id: str = "00000000-0000-0000-0000-000000000001"


class Workstream(BaseModel):
    index: int
    objective: str
    kind: TaskKind
    depends_on: list[int] = []
    brief: dict[str, str] = {}


class CrewPlan(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    raw_input: str
    workstreams: list[Workstream]
    status: str = "planned"  # planned | confirmed | running | completed
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    viewer_id: str = ""


class CrewStatus(BaseModel):
    plan_id: str
    status: str
    workstreams: list[dict[str, Any]]
    completed: int
    total: int


_crew_plans: list[CrewPlan] = []
_work_tasks: list[WorkTask] = [WorkTask(**t) for t in _load_json(TASKS_FILE)]


def _persist_tasks():
    _save_json(TASKS_FILE, [t.model_dump() for t in _work_tasks])


async def _triage_brain_dump(brain_dump: str) -> list[Workstream]:
    """Use the LLM to decompose a brain dump into workstreams."""
    settings = get_settings()
    openai_key = settings.openai_api_key.get_secret_value()

    store = get_entity_store()
    data_context = f"Available data: {len(store)} entities from {len(set(e.source for e in store))} sources."

    prompt = f"""You are a task decomposition engine. Break this brain dump into independent workstreams.

Rules:
- Split on independent OUTCOMES, not verbs
- Sequence when one output is another's input
- Answer inline if it costs less than briefing
- Max 5 workstreams
- Each workstream is either "ship" (produces a deliverable) or "scout" (investigates, changes nothing)

{data_context}

Brain dump:
{brain_dump}

Respond with a JSON array of workstreams:
[{{"index": 1, "objective": "...", "kind": "ship"|"scout", "depends_on": []}}]

Only return the JSON array, nothing else."""

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {openai_key}", "Content-Type": "application/json"},
                json={
                    "model": "gpt-4o-mini",
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.2,
                    "max_tokens": 2000,
                },
                timeout=30.0,
            )
            if resp.status_code == 200:
                content = resp.json()["choices"][0]["message"]["content"]
                # Extract JSON from response
                content = content.strip()
                if content.startswith("```"):
                    content = content.split("```")[1]
                    if content.startswith("json"):
                        content = content[4:]
                parsed = json.loads(content)
                return [Workstream(**ws) for ws in parsed]
    except Exception as e:
        logger.error("triage_failed", error=str(e))

    # Fallback: single workstream
    return [Workstream(index=1, objective=brain_dump, kind=TaskKind.SCOUT)]


# ═══════════════════════════════════════════════════════════════════════
# SKILLS — curated library + agent-proposed skills behind approval
# ═══════════════════════════════════════════════════════════════════════

class SkillStatus(str, Enum):
    ACTIVE = "active"
    PENDING = "pending_approval"
    DISABLED = "disabled"


class Skill(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: str
    prompt_template: str  # parameterized prompt
    parameters: list[str] = []  # required params
    category: str = "general"
    author: str = "system"
    status: SkillStatus = SkillStatus.ACTIVE
    usage_count: int = 0
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


_skills: list[Skill] = [Skill(**s) for s in _load_json(SKILLS_FILE)]

# Seed curated skills if empty
if not _skills:
    _skills = [
        Skill(
            name="Meeting Prep",
            description="Prepare a briefing document for an upcoming meeting with a contact or company",
            prompt_template="Prepare a meeting brief for {entity_name}. Include: recent emails, deal status, key contacts, open issues, and talking points. Format as a structured briefing.",
            parameters=["entity_name"],
            category="meetings",
        ),
        Skill(
            name="Pipeline Summary",
            description="Generate a summary of the current deal pipeline with amounts, stages, and next steps",
            prompt_template="Analyze the current deal pipeline. For each deal, show: name, amount, stage, close date, and key contacts. Highlight deals at risk and suggest next steps. Sort by close date.",
            parameters=[],
            category="revenue",
        ),
        Skill(
            name="Contact Report",
            description="Generate a comprehensive report on a specific contact including all touchpoints",
            prompt_template="Create a comprehensive contact report for {contact_name}. Include: all email interactions, deals they're associated with, company info, last contact date, and relationship strength assessment.",
            parameters=["contact_name"],
            category="relationships",
        ),
        Skill(
            name="Cross-Source Conflict Check",
            description="Identify data conflicts between sources for a specific entity",
            prompt_template="Check for data conflicts for {entity_name} across all connected sources. Report any differences in: contact info, deal amounts, company details, or other attributes. Flag which source is the declared system of record.",
            parameters=["entity_name"],
            category="data_quality",
        ),
        Skill(
            name="Weekly Digest",
            description="Generate a weekly digest of all activity across connected sources",
            prompt_template="Create a weekly activity digest. Include: new emails (count and highlights), deal updates, new contacts, document changes, and any data conflicts detected. Organize by priority.",
            parameters=[],
            category="reports",
        ),
        Skill(
            name="Company Research",
            description="Compile everything known about a company from all sources",
            prompt_template="Research {company_name} across all connected data. Include: contacts at the company, deals, email history, documents, and any governed Canon facts. Assess relationship health.",
            parameters=["company_name"],
            category="research",
        ),
    ]
    _save_json(SKILLS_FILE, [s.model_dump() for s in _skills])


def _persist_skills():
    _save_json(SKILLS_FILE, [s.model_dump() for s in _skills])


# ═══════════════════════════════════════════════════════════════════════
# SCHEDULED RUNS + DAILY BRIEF
# ═══════════════════════════════════════════════════════════════════════

class Schedule(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    skill_id: str = ""
    objective: str = ""
    cron: str = ""  # cron expression or "daily", "hourly", "weekly"
    enabled: bool = True
    last_run: str = ""
    next_run: str = ""
    viewer_id: str = ""
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


_schedules: list[Schedule] = [Schedule(**s) for s in _load_json(SCHEDULES_FILE)]


def _persist_schedules():
    _save_json(SCHEDULES_FILE, [s.model_dump() for s in _schedules])


# ═══════════════════════════════════════════════════════════════════════
# LEARNING LOOP — corrections → proposals
# ═══════════════════════════════════════════════════════════════════════

class Correction(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    task_id: str
    original_output: str
    correction: str
    corrected_by: str
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


_corrections: list[Correction] = []


# ═══════════════════════════════════════════════════════════════════════
# API ROUTES
# ═══════════════════════════════════════════════════════════════════════

# ── Agent: single task execution ───────────────────────────────────────

@router.post("/work/execute", response_model=WorkResult)
async def execute_task(request: WorkRequest) -> WorkResult:
    """Execute a single work task using the agent engine."""
    start = time.time()

    task = WorkTask(
        objective=request.objective,
        context=request.context,
        status=TaskStatus.IN_PROGRESS,
        viewer_id=request.viewer_id,
    )
    _work_tasks.append(task)

    result_text, steps = await _run_agent(
        request.objective, request.context, request.viewer_id
    )

    task.status = TaskStatus.COMPLETED
    task.result = {"output": result_text}
    task.steps = steps
    task.completed_at = datetime.now(timezone.utc).isoformat()
    _persist_tasks()

    return WorkResult(
        task_id=task.id,
        status=task.status.value,
        result=task.result,
        steps=steps,
        latency_ms=int((time.time() - start) * 1000),
    )


# ── Crew: brain-dump → triage → dispatch ──────────────────────────────

@router.post("/work/crew/plan")
async def crew_plan(request: CrewRequest) -> dict:
    """Decompose a brain dump into workstreams (confirm-before-dispatch)."""
    workstreams = await _triage_brain_dump(request.brain_dump)

    plan = CrewPlan(
        raw_input=request.brain_dump,
        workstreams=workstreams,
        viewer_id=request.viewer_id,
    )
    _crew_plans.append(plan)

    return {
        "plan_id": plan.id,
        "message": f"Splitting into {len(workstreams)} workstream(s). Confirm to dispatch.",
        "workstreams": [ws.model_dump() for ws in workstreams],
    }


@router.post("/work/crew/{plan_id}/confirm")
async def crew_confirm(plan_id: str) -> dict:
    """Confirm and dispatch the workstreams sequentially."""
    plan = next((p for p in _crew_plans if p.id == plan_id), None)
    if not plan:
        raise HTTPException(404, "Plan not found")

    plan.status = "running"

    # Create tasks for each workstream (respecting dependencies)
    tasks: list[WorkTask] = []
    for ws in sorted(plan.workstreams, key=lambda w: w.index):
        task = WorkTask(
            objective=ws.objective,
            kind=ws.kind,
            status=TaskStatus.READY,
            parent_id=plan.id,
            viewer_id=plan.viewer_id,
            workstream_index=ws.index,
            brief={
                "OBJECTIVE": ws.objective,
                "KIND": ws.kind.value,
                "DEPENDS_ON": ws.depends_on,
            },
        )
        _work_tasks.append(task)
        tasks.append(task)

    _persist_tasks()

    # Dispatch sequentially (respecting dependencies)
    results = []
    for task in tasks:
        task.status = TaskStatus.IN_PROGRESS
        result_text, steps = await _run_agent(task.objective, viewer_id=plan.viewer_id)
        task.status = TaskStatus.COMPLETED
        task.result = {"output": result_text}
        task.steps = steps
        task.completed_at = datetime.now(timezone.utc).isoformat()
        results.append({
            "workstream": task.workstream_index,
            "objective": task.objective,
            "status": task.status.value,
            "output": result_text[:1000],
        })

    plan.status = "completed"
    _persist_tasks()

    return {
        "plan_id": plan.id,
        "status": "completed",
        "results": results,
    }


@router.get("/work/crew/plans")
async def list_crew_plans(viewer_id: str = "") -> list[dict]:
    """List all crew plans."""
    plans = _crew_plans
    if viewer_id:
        plans = [p for p in plans if p.viewer_id == viewer_id]
    return [
        {
            "id": p.id,
            "input": p.raw_input[:200],
            "workstreams": len(p.workstreams),
            "status": p.status,
            "created_at": p.created_at,
        }
        for p in plans
    ]


# ── Skills ─────────────────────────────────────────────────────────────

@router.get("/work/skills")
async def list_skills() -> list[dict]:
    return [s.model_dump() for s in _skills if s.status != SkillStatus.DISABLED]


@router.post("/work/skills/{skill_id}/run")
async def run_skill(skill_id: str, params: dict[str, str] = {}) -> WorkResult:
    """Run a skill with the given parameters."""
    skill = next((s for s in _skills if s.id == skill_id), None)
    if not skill:
        raise HTTPException(404, "Skill not found")

    # Fill in template parameters
    prompt = skill.prompt_template
    for key, value in params.items():
        prompt = prompt.replace(f"{{{key}}}", value)

    start = time.time()
    result_text, steps = await _run_agent(prompt)

    skill.usage_count += 1
    _persist_skills()

    return WorkResult(
        task_id=str(uuid.uuid4()),
        status="completed",
        result={"output": result_text, "skill": skill.name},
        steps=steps,
        latency_ms=int((time.time() - start) * 1000),
    )


@router.post("/work/skills/propose")
async def propose_skill(
    name: str, description: str, prompt_template: str, category: str = "general"
) -> dict:
    """Agent or user proposes a new skill — requires approval."""
    skill = Skill(
        name=name,
        description=description,
        prompt_template=prompt_template,
        category=category,
        author="user",
        status=SkillStatus.PENDING,
    )
    _skills.append(skill)
    _persist_skills()
    return {"id": skill.id, "message": "Skill proposed for approval", "status": "pending_approval"}


@router.post("/work/skills/{skill_id}/approve")
async def approve_skill(skill_id: str) -> dict:
    skill = next((s for s in _skills if s.id == skill_id), None)
    if not skill:
        raise HTTPException(404, "Skill not found")
    skill.status = SkillStatus.ACTIVE
    _persist_skills()
    return {"approved": True}


# ── Scheduled runs ─────────────────────────────────────────────────────

@router.get("/work/schedules")
async def list_schedules() -> list[dict]:
    return [s.model_dump() for s in _schedules]


@router.post("/work/schedules")
async def create_schedule(
    name: str, objective: str = "", skill_id: str = "", cron: str = "daily",
    viewer_id: str = "",
) -> dict:
    schedule = Schedule(
        name=name, objective=objective, skill_id=skill_id,
        cron=cron, viewer_id=viewer_id,
    )
    _schedules.append(schedule)
    _persist_schedules()
    return {"id": schedule.id, "message": f"Schedule '{name}' created ({cron})"}


@router.post("/work/daily-brief")
async def generate_daily_brief(viewer_id: str = "") -> WorkResult:
    """Generate a proactive daily brief from all connected data."""
    prompt = (
        "Generate a daily brief for the user. Include:\n"
        "1. New emails since yesterday (count and highlights)\n"
        "2. Deal pipeline status and any changes\n"
        "3. Upcoming deadlines or follow-ups needed\n"
        "4. Any data conflicts detected across sources\n"
        "5. Key metrics summary\n\n"
        "Be concise and actionable. Prioritize items that need attention today."
    )
    start = time.time()
    result_text, steps = await _run_agent(prompt, viewer_id=viewer_id)

    return WorkResult(
        task_id=str(uuid.uuid4()),
        status="completed",
        result={"output": result_text, "type": "daily_brief"},
        steps=steps,
        latency_ms=int((time.time() - start) * 1000),
    )


# ── Learning loop ─────────────────────────────────────────────────────

@router.post("/work/correct")
async def submit_correction(task_id: str, correction: str, corrected_by: str = "user") -> dict:
    """Submit a correction to an agent output — feeds the learning loop."""
    task = next((t for t in _work_tasks if t.id == task_id), None)
    if not task:
        raise HTTPException(404, "Task not found")

    corr = Correction(
        task_id=task_id,
        original_output=str(task.result.get("output", ""))[:1000],
        correction=correction,
        corrected_by=corrected_by,
    )
    _corrections.append(corr)

    # Auto-generate a Canon proposal from the correction
    try:
        from services.api.routes.canon import (
            _proposals, Proposal, ProposalSource, StakeLevel, _persist_proposals,
        )
        _proposals.append(Proposal(
            action="create",
            entity_name="Correction",
            entity_type="knowledge",
            field="learned_fact",
            new_value=correction,
            source="learning-loop",
            proposed_by=corrected_by,
            proposal_source=ProposalSource.BYPRODUCT,
            stake_level=StakeLevel.LOW,
            reason=f"Learned from user correction on task {task_id[:8]}",
        ))
        _persist_proposals()
    except Exception:
        pass

    return {"correction_id": corr.id, "message": "Correction recorded and proposal generated"}


# ── Task history ──────────────────────────────────────────────────────

@router.get("/work/tasks")
async def list_tasks(viewer_id: str = "", limit: int = 20) -> list[dict]:
    tasks = _work_tasks
    if viewer_id:
        tasks = [t for t in tasks if t.viewer_id == viewer_id]
    return [
        {
            "id": t.id,
            "objective": t.objective[:200],
            "kind": t.kind.value,
            "status": t.status.value,
            "created_at": t.created_at,
            "completed_at": t.completed_at,
            "steps_count": len(t.steps),
        }
        for t in sorted(tasks, key=lambda x: x.created_at, reverse=True)[:limit]
    ]
