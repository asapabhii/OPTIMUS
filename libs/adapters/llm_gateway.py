"""LLM gateway adapter — abstract interface for model routing.

Commercial: Portkey (virtual keys with per-key model allow-lists)
OSS fallback: LiteLLM Enterprise (config swap — OpenAI-compatible throughout)

Model routing is by TASK CLASS, never user preference (P28).
Canon-touching calls use the APPROVED model only — no override (REQ-13.2).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, AsyncIterator

from core.enums import TaskClass


@dataclass
class LLMRequest:
    """A request to the LLM gateway."""

    task_class: TaskClass
    messages: list[dict[str, str]]
    temperature: float = 0.0
    max_tokens: int = 4096
    response_format: dict[str, Any] | None = None
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass
class LLMResponse:
    """Response from the LLM gateway."""

    content: str
    model_used: str
    usage: dict[str, int]
    cost_usd: float | None = None
    latency_ms: int = 0


class LLMGatewayAdapter(ABC):
    """Abstract LLM gateway.

    Implementations MUST:
    - Route requests to the correct model tier based on task_class
    - Enforce that CANON_MUTATION tasks use only the approved model
    - Track per-task-class costs (for G11 extraction cost model)
    - Support structured output (for extraction)
    """

    @abstractmethod
    async def complete(self, request: LLMRequest) -> LLMResponse:
        """Complete a request, routed by task class."""

    @abstractmethod
    async def stream(self, request: LLMRequest) -> AsyncIterator[str]:
        """Stream a completion, routed by task class."""

    @abstractmethod
    async def get_cost_by_task_class(self) -> dict[str, float]:
        """Get accumulated costs per task class (for G11)."""

    @abstractmethod
    async def health_check(self) -> bool:
        """Liveness check."""
