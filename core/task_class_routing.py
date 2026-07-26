"""P28: Task-class routing table — model selection by task class.

Model selection is routed by TASK CLASS, never user preference.
Given a free choice, users pick the most capable model for everything
and then object to the cost.

The CANON_MUTATION row is a HARD RULE (REQ-13.2). This is where
confabulation stops being a bad answer and becomes corrupted
organizational data. Applies with full force to bulk-authoring
extraction (REQ-6.10), where canon is extracted at volume.
"""

from __future__ import annotations

from dataclasses import dataclass

from core.enums import ModelTier, TaskClass


@dataclass(frozen=True)
class TaskClassRoute:
    """Maps a task class to a model tier and Portkey virtual key."""

    task_class: TaskClass
    model_tier: ModelTier
    description: str
    portkey_virtual_key: str = ""  # Set per environment
    model_allow_list: list[str] | None = None


# ─────────────────────────────────────────────────────────────
# THE ROUTING TABLE
# ─────────────────────────────────────────────────────────────

TASK_CLASS_ROUTES: dict[TaskClass, TaskClassRoute] = {
    TaskClass.CLASSIFICATION: TaskClassRoute(
        task_class=TaskClass.CLASSIFICATION,
        model_tier=ModelTier.CHEAPEST_ADEQUATE,
        description="High volume, low stakes — classification, triage, freshness inference",
        model_allow_list=["gpt-4o-mini", "deepseek-chat", "qwen-turbo"],
    ),
    TaskClass.EXTRACTION: TaskClassRoute(
        task_class=TaskClass.EXTRACTION,
        model_tier=ModelTier.CHEAPEST_ADEQUATE,
        description="Structured extraction from parsed documents — high volume",
        model_allow_list=["gpt-4o-mini", "deepseek-chat"],
    ),
    TaskClass.RETRIEVAL_PLANNING: TaskClassRoute(
        task_class=TaskClass.RETRIEVAL_PLANNING,
        model_tier=ModelTier.MID_TIER,
        description="Query planning, link-set emission, fan-out decisions",
        model_allow_list=["gpt-4o", "claude-sonnet-4-20250514"],
    ),
    TaskClass.SYNTHESIS: TaskClassRoute(
        task_class=TaskClass.SYNTHESIS,
        model_tier=ModelTier.MOST_CAPABLE,
        description="Answer synthesis, reasoning, conflict arbitration rendering",
        model_allow_list=["gpt-4o", "claude-sonnet-4-20250514", "claude-opus-4-20250514"],
    ),
    TaskClass.CANON_MUTATION: TaskClassRoute(
        task_class=TaskClass.CANON_MUTATION,
        model_tier=ModelTier.APPROVED_ONLY,
        description="ANYTHING touching the canon or write-back. NO OVERRIDE. "
                    "A weaker model's confabulation here is corrupted organizational data.",
        model_allow_list=["gpt-4o"],  # The ONE approved model
    ),
}


def get_route(task_class: TaskClass) -> TaskClassRoute:
    """Get the routing config for a task class.

    Never returns None — every task class MUST have a route.
    """
    route = TASK_CLASS_ROUTES.get(task_class)
    if route is None:
        msg = f"No routing config for task class {task_class}. This is a configuration error."
        raise ValueError(msg)
    return route
