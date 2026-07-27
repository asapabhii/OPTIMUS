"""Phase 0 spike: Splink + RapidFuzz entity resolution against the fixture.

THE TEST: Run the labeled ER corpus through the SplinkRapidFuzzResolver
and measure precision.

Success criteria:
  - Auto-merge precision >= 0.98 on the labeled corpus
  - Non-person entities (SKUs, projects) resolve correctly
  - Explainable match output for the review queue
  - Runs entirely in-process (data never leaves our boundary)
  - Zero licensing cost (MIT + MIT)
"""

from __future__ import annotations

import asyncio

from fixture.labeled_pairs.er_corpus import LABELED_PAIRS
from libs.adapters.impl.splink_resolver import SplinkRapidFuzzResolver
from libs.adapters.resolver import ResolveCandidate


async def run_spike() -> None:
    """Run the Splink+RapidFuzz ER precision spike."""

    print(f"Labeled corpus: {len(LABELED_PAIRS)} pairs")
    positives = sum(1 for _, _, m in LABELED_PAIRS if m)
    negatives = sum(1 for _, _, m in LABELED_PAIRS if not m)
    print(f"  Positive (should match): {positives}")
    print(f"  Negative (should NOT match): {negatives}")

    resolver = SplinkRapidFuzzResolver()

    true_positives = 0
    false_positives = 0
    false_negatives = 0
    true_negatives = 0

    for name_a, name_b, should_match in LABELED_PAIRS:
        # Register name_a as a known entity
        candidate_a = ResolveCandidate(
            source_id="spike-test",
            source_ref=f"ref-{name_a}",
            entity_type="company",
            name=name_a,
            attributes={},
        )
        resolver._register_entity(f"ent-{name_a}", candidate_a)

        # Try to resolve name_b against it
        candidate_b = ResolveCandidate(
            source_id="spike-test",
            source_ref=f"ref-{name_b}",
            entity_type="company",
            name=name_b,
            attributes={},
        )
        result = await resolver.resolve(candidate_b)
        predicted_match = result.matched_entity_id is not None and not result.is_conflict

        if predicted_match and should_match:
            true_positives += 1
        elif predicted_match and not should_match:
            false_positives += 1
            print(f"  FP: '{name_a}' <-> '{name_b}' matched at {result.confidence:.2f}")
            print(f"       {result.explanation}")
        elif not predicted_match and should_match:
            false_negatives += 1
            print(f"  FN: '{name_a}' <-> '{name_b}' did NOT match ({result.confidence:.2f})")
            print(f"       {result.explanation}")
        else:
            true_negatives += 1

        # Clean up for next pair (each pair is independent)
        resolver._entities.clear()
        resolver._records.clear()

    precision = (
        true_positives / (true_positives + false_positives)
        if (true_positives + false_positives) > 0 else 0.0
    )
    recall = (
        true_positives / (true_positives + false_negatives)
        if (true_positives + false_negatives) > 0 else 0.0
    )
    f1 = (
        2 * precision * recall / (precision + recall)
        if (precision + recall) > 0 else 0.0
    )

    print(f"\n{'='*50}")
    print(f"Results (Splink + RapidFuzz):")
    print(f"  TP={true_positives}  FP={false_positives}  FN={false_negatives}  TN={true_negatives}")
    print(f"  Precision: {precision:.4f} (target: >= 0.98)")
    print(f"  Recall:    {recall:.4f}")
    print(f"  F1:        {f1:.4f}")

    if precision >= 0.98:
        print(f"\n  ✓ PASS — Gate-1 threshold met. Proceed with Splink + RapidFuzz.")
    else:
        print(f"\n  ✗ FAIL — Below Gate-1 threshold.")
        print(f"  Action: Review false positives, tune thresholds, consider attribute comparisons.")


if __name__ == "__main__":
    asyncio.run(run_spike())
