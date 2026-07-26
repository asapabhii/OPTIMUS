"""Authorization adapter — abstract interface for the audience-tag gate.

Commercial: AuthZed Cloud or Cerbos (OD-2 — decided at Gate 4 benchmark)
OSS fallback: Permify (Apache 2.0, self-hostable) — never a hand-roll

NOTE: This is the AUDIENCE gate only. The SOURCE gate is always the live
viewer-token check via Nango (P21: two independent gates, never collapsed).
The job here is deliberately small: audience-tag visibility over a small canon.
"""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod


class AuthAdapter(ABC):
    """Abstract authorization engine for audience-tag gating.

    Not used in Phase 1 (single-player). Ships at Gate 4 (F-P2).
    The interface is defined from commit one per the adapter discipline.
    """

    @abstractmethod
    async def check_permission(
        self,
        viewer_id: uuid.UUID,
        resource_type: str,
        resource_id: str,
        permission: str,
    ) -> bool:
        """Check if a viewer has a specific permission on a resource."""

    @abstractmethod
    async def filter_accessible(
        self,
        viewer_id: uuid.UUID,
        resource_type: str,
        resource_ids: list[str],
        permission: str,
    ) -> list[str]:
        """Filter a list of resources to only those accessible by the viewer."""

    @abstractmethod
    async def health_check(self) -> bool:
        """Liveness check."""
