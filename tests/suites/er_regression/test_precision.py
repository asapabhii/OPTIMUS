"""ER regression suite — tracks entity resolution precision over time.

Gate-1 stop-test: >=0.98 auto-merge precision on the labeled corpus.
Uses Splink + RapidFuzz (MIT, zero licensing cost).
"""

from __future__ import annotations

import pytest

from fixture.labeled_pairs.er_corpus import LABELED_PAIRS


@pytest.mark.er_regression
class TestERPrecision:
    """Entity resolution precision tracking against the labeled corpus."""

    def test_corpus_has_sufficient_pairs(self) -> None:
        """Ensure we have enough labeled pairs for a meaningful test."""
        assert len(LABELED_PAIRS) >= 150, (
            f"Need >=150 labeled pairs for Gate-1 stop-test, have {len(LABELED_PAIRS)}"
        )

    def test_corpus_has_balanced_labels(self) -> None:
        """Ensure positive and negative labels are balanced."""
        positives = sum(1 for _, _, match in LABELED_PAIRS if match)
        negatives = sum(1 for _, _, match in LABELED_PAIRS if not match)
        ratio = positives / negatives if negatives > 0 else float("inf")

        assert 0.4 < ratio < 2.5, (
            f"Label imbalance: {positives} positives, {negatives} negatives "
            f"(ratio: {ratio:.2f}). Need roughly balanced labels."
        )

    def test_corpus_includes_non_person_entities(self) -> None:
        """Verify the resolver handles SKUs, companies, and projects — not just persons."""
        non_person_indicators = ["Assembly", "SKU", "IND-", "Monitor", "Printer", "Server", "Mouse", "Hub", "Keyboard"]
        has_non_person = any(
            any(ind in a or ind in b for ind in non_person_indicators)
            for a, b, _ in LABELED_PAIRS
        )
        assert has_non_person, "Corpus must include non-person entities (SKUs, products)"

    @pytest.mark.asyncio
    async def test_precision_above_threshold(self) -> None:
        """Gate-1 stop-test: auto-merge precision >=0.98.

        Runs the full labeled corpus through SplinkRapidFuzzResolver.
        """
        from libs.adapters.impl.splink_resolver import SplinkRapidFuzzResolver
        from libs.adapters.resolver import ResolveCandidate

        resolver = SplinkRapidFuzzResolver()
        true_positives = 0
        false_positives = 0

        for name_a, name_b, should_match in LABELED_PAIRS:
            candidate_a = ResolveCandidate(
                source_id="test", source_ref=f"ref-{name_a}",
                entity_type="company", name=name_a, attributes={},
            )
            resolver._register_entity(f"ent-{name_a}", candidate_a)

            candidate_b = ResolveCandidate(
                source_id="test", source_ref=f"ref-{name_b}",
                entity_type="company", name=name_b, attributes={},
            )
            result = await resolver.resolve(candidate_b)
            predicted_match = (
                result.matched_entity_id is not None
                and not result.is_conflict
            )

            if predicted_match and should_match:
                true_positives += 1
            elif predicted_match and not should_match:
                false_positives += 1

            resolver._entities.clear()
            resolver._records.clear()

        precision = (
            true_positives / (true_positives + false_positives)
            if (true_positives + false_positives) > 0 else 0.0
        )
        assert precision >= 0.98, (
            f"Gate-1 precision {precision:.4f} < 0.98. "
            f"TP={true_positives}, FP={false_positives}. "
            f"Review false positives and tune thresholds."
        )
