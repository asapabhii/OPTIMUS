"""Shared test fixtures."""

from __future__ import annotations

import os
import uuid

import pytest


@pytest.fixture(autouse=True)
def _set_test_env() -> None:
    """Set test environment variables — autouse so Settings never crashes."""
    os.environ.setdefault("APP_ENV", "test")
    os.environ.setdefault(
        "DATABASE_URL",
        "postgresql+asyncpg://optimus:optimus_test@localhost:5432/optimus_test",
    )
    os.environ.setdefault(
        "DATABASE_URL_SYNC",
        "postgresql://optimus:optimus_test@localhost:5432/optimus_test",
    )
    os.environ.setdefault("NANGO_SECRET_KEY", "test-nango-key")
    os.environ.setdefault("PORTKEY_API_KEY", "test-portkey-key")
    os.environ.setdefault("OPENAI_API_KEY", "test-openai-key")


@pytest.fixture
def viewer_id() -> uuid.UUID:
    """A test viewer ID."""
    return uuid.UUID("00000000-0000-0000-0000-000000000001")
