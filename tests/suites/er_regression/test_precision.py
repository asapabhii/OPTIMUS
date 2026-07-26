"""ER regression suite — tracks entity resolution precision over time.

Gate-1 stop-test: >=0.98 auto-merge precision on the labeled corpus.
This decides Senzing vs. Splink empirically, not by preference.
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
        """Senzing traditionally does person resolution.
        We need to verify it handles SKUs, companies, projects too.
        """
        non_person_indicators = ["Assembly", "SKU", "IND-", "Monitor", "Printer", "Server", "Mouse", "Hub", "Keyboard"]
        has_non_person = any(
            any(ind in a or ind in b for ind in non_person_indicators)
            for a, b, _ in LABELED_PAIRS
        )
        assert has_non_person, "Corpus must include non-person entities (SKUs, products)"

    @pytest.mark.skip(reason="Requires Senzing SDK — run after Gate-1 spike")
    def test_precision_above_threshold(self) -> None:
        """Gate-1 stop-test: auto-merge precision >=0.98.

        TODO: Wire to ResolverAdapter implementation.
        Run each labeled pair through the resolver and measure precision.
        """
        # true_positives = 0
        # false_positives = 0
        # for name_a, name_b, should_match in LABELED_PAIRS:
        #     result = await resolver.resolve(...)
        #     predicted_match = result.confidence >= THRESHOLD
        #     if predicted_match and should_match:
        #         true_positives += 1
        #     elif predicted_match and not should_match:
        #         false_positives += 1
        # precision = true_positives / (true_positives + false_positives)
        # assert precision >= 0.98
        pass
