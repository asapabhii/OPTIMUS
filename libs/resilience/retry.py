"""Retry with exponential backoff + jitter.

All retryable vendor calls use this. Non-retryable errors
(auth failures, 4xx) are NOT retried.
"""

from __future__ import annotations

from typing import Any, Callable, TypeVar

from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential_jitter,
)

from libs.observability.logging import get_logger

logger = get_logger("retry")

F = TypeVar("F", bound=Callable[..., Any])


def retryable(
    max_attempts: int = 3,
    min_wait: float = 0.5,
    max_wait: float = 10.0,
    retryable_exceptions: tuple[type[Exception], ...] = (
        ConnectionError,
        TimeoutError,
    ),
) -> Callable[[F], F]:
    """Decorator for retryable async operations with exponential backoff + jitter."""

    return retry(  # type: ignore[return-value]
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential_jitter(initial=min_wait, max=max_wait, jitter=min_wait),
        retry=retry_if_exception_type(retryable_exceptions),
        before_sleep=lambda retry_state: logger.warning(
            "retrying",
            attempt=retry_state.attempt_number,
            wait=retry_state.next_action.sleep if retry_state.next_action else 0,
        ),
    )
