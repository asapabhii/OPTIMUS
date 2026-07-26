"""Shared test fixtures."""

from __future__ import annotations

import os
import uuid

import pytest


@pytest.fixture
def viewer_id() -> uuid.UUID:
    """A test viewer ID."""
    return uuid.UUID("00000000-0000-0000-0000-000000000001")


@pytest.fixture
def test_env() -> None:
    """Set test environment variables."""
    os.environ.setdefault("APP_ENV", "test")
    os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://optimus:test@localhost/optimus_test")
    os.environ.setdefault("DATABASE_URL_SYNC", "postgresql://optimus:test@localhost/optimus_test")
    os.environ.setdefault("NANGO_SECRET_KEY", "test-key")
    os.environ.setdefault("PORTKEY_API_KEY", "test-key")
    os.environ.setdefault("OPENAI_API_KEY", "test-key")
