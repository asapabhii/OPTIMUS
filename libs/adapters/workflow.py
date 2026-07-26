"""Workflow adapter — abstract interface for durable execution.

Commercial: Temporal Cloud
OSS fallback: Self-hosted Temporal (same SDK, same code)

Used for:
- Per-viewer reconciliation workflows (Plane A)
- Proposal workflows (Gate 5)
- Write-back sagas with dry-run + revert (Gate 7)
- TTL expiry on canon facts
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class WorkflowExecution:
    """A running or completed workflow."""

    workflow_id: str
    run_id: str
    status: str  # RUNNING, COMPLETED, FAILED, CANCELLED, TIMED_OUT
    result: Any = None


class WorkflowAdapter(ABC):
    """Abstract workflow engine.

    The checkpoint invariant: the agent loop NEVER runs inside
    a workflow. Temporal owns lifecycle; the engine owns cognition.
    """

    @abstractmethod
    async def start_workflow(
        self,
        workflow_type: str,
        workflow_id: str,
        args: dict[str, Any],
        task_queue: str = "default",
    ) -> WorkflowExecution:
        """Start a workflow execution."""

    @abstractmethod
    async def get_workflow_status(self, workflow_id: str) -> WorkflowExecution:
        """Get the status of a workflow."""

    @abstractmethod
    async def signal_workflow(
        self, workflow_id: str, signal_name: str, data: Any = None
    ) -> None:
        """Send a signal to a running workflow."""

    @abstractmethod
    async def cancel_workflow(self, workflow_id: str) -> None:
        """Cancel a running workflow."""

    @abstractmethod
    async def health_check(self) -> bool:
        """Liveness check."""
