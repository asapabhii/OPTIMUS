"""Unit tests for the policy engine classifier."""

from __future__ import annotations

import pytest

from core.enums import CostOfStaleness, SourceClass, VolatilityClass
from core.freshness_table import FreshnessEntry
from engine.policy.classifier import classify_freshness, get_pipeline


class TestClassifier:
    """Freshness classification via the inference ladder."""

    @pytest.mark.asyncio
    async def test_known_provider_artifact(self) -> None:
        """Known provider + artifact → table lookup."""
        result = await classify_freshness("hubspot", "deal")
        assert result.volatility_class == VolatilityClass.LIVE_STATE
        assert result.cost_of_staleness == CostOfStaleness.CRITICAL
        assert result.source_class == SourceClass.AUTHORITY

    @pytest.mark.asyncio
    async def test_email_is_evidence(self) -> None:
        """Email is always evidence (P7)."""
        result = await classify_freshness("gmail", "email")
        assert result.source_class == SourceClass.EVIDENCE
        assert result.volatility_class == VolatilityClass.APPEND_ONLY

    @pytest.mark.asyncio
    async def test_user_declaration_overrides(self) -> None:
        """User declaration always wins."""
        override = FreshnessEntry(
            provider_type="hubspot",
            artifact_type="deal",
            volatility_class=VolatilityClass.SLOW_STATE,
            cost_of_staleness=CostOfStaleness.LOW,
            source_class=SourceClass.EVIDENCE,
        )
        result = await classify_freshness("hubspot", "deal", user_declaration=override)
        assert result.volatility_class == VolatilityClass.SLOW_STATE

    @pytest.mark.asyncio
    async def test_unknown_falls_back(self) -> None:
        """Unknown provider + artifact → conservative fallback."""
        result = await classify_freshness("unknown_tool", "unknown_artifact")
        assert result.volatility_class == VolatilityClass.SLOW_STATE
        assert result.source_class == SourceClass.EVIDENCE


class TestPipelineRouting:
    """Route artifacts to the correct freshness pipeline."""

    def test_frozen_goes_immutable(self) -> None:
        entry = FreshnessEntry("x", "y", VolatilityClass.FROZEN, CostOfStaleness.LOW, SourceClass.AUTHORITY)
        assert get_pipeline(entry) == "immutable"

    def test_append_only_goes_immutable(self) -> None:
        entry = FreshnessEntry("x", "y", VolatilityClass.APPEND_ONLY, CostOfStaleness.LOW, SourceClass.EVIDENCE)
        assert get_pipeline(entry) == "immutable"

    def test_slow_state_goes_slow(self) -> None:
        entry = FreshnessEntry("x", "y", VolatilityClass.SLOW_STATE, CostOfStaleness.MEDIUM, SourceClass.AUTHORITY)
        assert get_pipeline(entry) == "slow"

    def test_live_state_goes_live(self) -> None:
        entry = FreshnessEntry("x", "y", VolatilityClass.LIVE_STATE, CostOfStaleness.CRITICAL, SourceClass.AUTHORITY)
        assert get_pipeline(entry) == "live"
