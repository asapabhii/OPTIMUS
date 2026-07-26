"""Unit tests for the belief engine."""

from __future__ import annotations

import uuid

import pytest

from engine.belief.engine import compute_evidence_set_hash, compute_confidence, apply_degradation_factor


class TestEvidenceSetHash:
    """Evidence-set hash is the memoization key."""

    def test_deterministic_hash(self) -> None:
        """Same evidence set → same hash."""
        ids = [uuid.uuid4(), uuid.uuid4(), uuid.uuid4()]
        hash1 = compute_evidence_set_hash(ids)
        hash2 = compute_evidence_set_hash(ids)
        assert hash1 == hash2

    def test_order_independent(self) -> None:
        """Hash is order-independent (sorted internally)."""
        id1, id2, id3 = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
        hash_a = compute_evidence_set_hash([id1, id2, id3])
        hash_b = compute_evidence_set_hash([id3, id1, id2])
        assert hash_a == hash_b

    def test_different_sets_different_hash(self) -> None:
        """Different evidence sets → different hashes."""
        set_a = [uuid.uuid4(), uuid.uuid4()]
        set_b = [uuid.uuid4(), uuid.uuid4()]
        assert compute_evidence_set_hash(set_a) != compute_evidence_set_hash(set_b)

    def test_empty_set(self) -> None:
        """Empty evidence set produces a valid hash."""
        h = compute_evidence_set_hash([])
        assert isinstance(h, str) and len(h) == 64


class TestConfidence:
    """Confidence computation."""

    def test_zero_evidence(self) -> None:
        assert compute_confidence(0, 0) == 0.0

    def test_single_evidence(self) -> None:
        conf = compute_confidence(1, 1)
        assert 0.5 <= conf <= 0.7

    def test_many_evidence(self) -> None:
        conf = compute_confidence(10, 10)
        assert conf <= 0.95

    def test_caps_at_max(self) -> None:
        conf = compute_confidence(100, 100)
        assert conf == 0.95


class TestDegradation:
    """Partial evidence loss degrades confidence."""

    def test_full_loss(self) -> None:
        degraded = apply_degradation_factor(0.8, 3, 0)
        assert degraded == 0.0

    def test_no_loss(self) -> None:
        degraded = apply_degradation_factor(0.8, 3, 3)
        assert degraded == 0.8

    def test_partial_loss(self) -> None:
        degraded = apply_degradation_factor(0.9, 3, 2)
        assert degraded < 0.9
        assert degraded > 0.0

    def test_minimum_floor(self) -> None:
        degraded = apply_degradation_factor(0.9, 100, 1)
        assert degraded >= 0.1
