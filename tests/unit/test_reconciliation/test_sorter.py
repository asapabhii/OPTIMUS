"""Unit tests for the reconciliation three-way sorter."""

from __future__ import annotations

import uuid

import pytest

from core.enums import SortOutcome


class TestSortOutcome:
    """Three-way sort produces exactly one outcome per candidate."""

    def test_novel_outcome(self) -> None:
        assert SortOutcome.NOVEL.value == "novel"

    def test_confident_outcome(self) -> None:
        assert SortOutcome.CONFIDENT_MATCH.value == "confident"

    def test_conflict_outcome(self) -> None:
        assert SortOutcome.CONFLICT.value == "conflict"

    def test_all_outcomes_distinct(self) -> None:
        outcomes = [SortOutcome.NOVEL, SortOutcome.CONFIDENT_MATCH, SortOutcome.CONFLICT]
        assert len(set(outcomes)) == 3
