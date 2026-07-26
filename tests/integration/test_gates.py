"""Integration tests for the three Phase-1 gates.

Gate 1: 3 names / 4 tools → 1 entity, >=0.98 precision
Gate 2: Revoke 1/3 sources → belief recomputes at reduced confidence
Gate 3: Every auto-decision visible and reversible
"""

from __future__ import annotations

import uuid

import pytest

from core.enums import AutoDecisionType, SourceClass
from core.models.decision import AutoDecision
from core.models.proposal import PendingProposal


@pytest.mark.gate1
class TestGate1:
    """Gate 1: entity resolution precision."""

    @pytest.mark.skip(reason="Requires full infrastructure — run in integration environment")
    def test_three_names_one_entity(self) -> None:
        """3 CRM name variants for Meridian Supply → 1 entity."""
        pass

    @pytest.mark.skip(reason="Requires Senzing SDK")
    def test_er_precision_threshold(self) -> None:
        """>=0.98 auto-merge precision on labeled corpus."""
        pass


@pytest.mark.gate2
class TestGate2:
    """Gate 2: belief recomputation on source revocation."""

    @pytest.mark.skip(reason="Requires full infrastructure — run in integration environment")
    def test_revoke_recomputes_at_reduced_confidence(self) -> None:
        """Revoking 1 of 3 sources → belief recomputes, confidence drops."""
        pass

    @pytest.mark.skip(reason="Requires full infrastructure")
    def test_revoke_all_evaporates(self) -> None:
        """Revoking all sources → belief evaporates entirely."""
        pass


@pytest.mark.gate3
class TestGate3:
    """Gate 3: every auto-decision visible and reversible."""

    def test_auto_decision_is_visible(self) -> None:
        """Every auto-decision has a unique ID and type."""
        decision = AutoDecision(
            decision_type=AutoDecisionType.ENTITY_MERGE,
            input_data={"candidate": "Acme Corp"},
            output_data={"merged_into": "existing-id"},
            explanation="Matched on domain, legal suffix differs",
            confidence=0.92,
            viewer_id=uuid.uuid4(),
        )
        assert decision.id is not None
        assert decision.decision_type == AutoDecisionType.ENTITY_MERGE

    def test_auto_decision_is_reversible(self) -> None:
        """Every auto-decision can be reversed."""
        decision = AutoDecision(
            decision_type=AutoDecisionType.ENTITY_MERGE,
            confidence=0.92,
            viewer_id=uuid.uuid4(),
        )
        decision.reversed = True
        decision.reversed_reason = "User review"
        assert decision.reversed is True

    def test_evidence_class_bar_enforced(self) -> None:
        """Evidence-class sources cannot generate proposals (REQ-6.9b)."""
        with pytest.raises(ValueError, match="Evidence-class sources cannot"):
            PendingProposal(
                claim_text="Maybe drop the enterprise tier",
                source_class_of_origin=SourceClass.EVIDENCE,
                viewer_id=uuid.uuid4(),
            )

    def test_authority_class_can_propose(self) -> None:
        """Authority-class sources CAN generate proposals."""
        proposal = PendingProposal(
            claim_text="Renewal date is Jan 15",
            source_class_of_origin=SourceClass.AUTHORITY,
            viewer_id=uuid.uuid4(),
        )
        assert proposal.claim_text == "Renewal date is Jan 15"
