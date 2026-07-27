"""Per-vendor circuit breakers.

Every external call (Nango, Portkey, Qdrant, etc.) goes through
a circuit breaker. When a vendor is down, we fail fast rather than
accumulating timeouts.
"""

from __future__ import annotations

from circuitbreaker import circuit
from functools import wraps
from typing import Any, Callable, TypeVar

from libs.observability.logging import get_logger

logger = get_logger("circuit_breaker")

F = TypeVar("F", bound=Callable[..., Any])


def vendor_circuit_breaker(
    vendor_name: str,
    failure_threshold: int = 5,
    recovery_timeout: int = 30,
    expected_exception: type[Exception] = Exception,
) -> Callable[[F], F]:
    """Create a circuit breaker for a specific vendor.

    Args:
        vendor_name: Name for logging (e.g., "nango", "portkey")
        failure_threshold: Number of failures before opening
        recovery_timeout: Seconds before attempting recovery
        expected_exception: Exception type that counts as a failure
    """

    def decorator(func: F) -> F:
        @circuit(
            failure_threshold=failure_threshold,
            recovery_timeout=recovery_timeout,
            expected_exception=expected_exception,
            name=f"cb_{vendor_name}",
        )
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                logger.warning(
                    "vendor_call_failed",
                    vendor=vendor_name,
                    error=str(e),
                    function=func.__name__,
                )
                raise

        return wrapper  # type: ignore[return-value]

    return decorator
