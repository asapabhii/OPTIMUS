"""Timeout policies per operation type.

Plane B has a 500ms p50 budget. Every vendor call within that path
has a strict timeout to defend the overall budget.
"""

from __future__ import annotations

import asyncio
from functools import wraps
from typing import Any, Callable, TypeVar

from libs.observability.logging import get_logger

logger = get_logger("timeout")

F = TypeVar("F", bound=Callable[..., Any])


# Timeout budgets by operation type (milliseconds)
TIMEOUT_BUDGETS_MS = {
    "live_read": 2000,           # MCP live read via Nango
    "permission_ping": 1000,     # Per-claim permission verification
    "vector_search": 500,        # Qdrant evidence search
    "belief_recompute": 3000,    # LLM call for belief recomputation
    "extraction": 30000,         # LLM structured extraction (Plane A, relaxed)
    "parsing": 60000,            # Document parsing (Plane A, relaxed)
    "entity_resolution": 5000,   # Splink + RapidFuzz resolve
    "default": 5000,
}


def with_timeout(
    operation: str = "default",
    timeout_ms: int | None = None,
) -> Callable[[F], F]:
    """Timeout decorator with operation-specific budgets."""

    def decorator(func: F) -> F:
        budget = timeout_ms or TIMEOUT_BUDGETS_MS.get(
            operation, TIMEOUT_BUDGETS_MS["default"]
        )

        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return await asyncio.wait_for(
                    func(*args, **kwargs),
                    timeout=budget / 1000.0,
                )
            except asyncio.TimeoutError:
                logger.error(
                    "operation_timeout",
                    operation=operation,
                    timeout_ms=budget,
                    function=func.__name__,
                )
                raise TimeoutError(
                    f"{operation} timed out after {budget}ms"
                ) from None

        return wrapper  # type: ignore[return-value]

    return decorator
