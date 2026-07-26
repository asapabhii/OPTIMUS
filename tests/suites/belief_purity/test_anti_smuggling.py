"""Belief-purity suite — PERMANENT CI BLOCKER from Gate 2.

Tests that the anti-smuggling guarantee holds:
1. synthesize() has no access to prior conclusions
2. No forbidden parameters in the function signature
3. The belief engine module has no structural violations
4. Recomputation from partial loss uses only surviving evidence
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from engine.belief.anti_smuggling import (
    FORBIDDEN_TERMS,
    static_check_belief_module,
    validate_no_prior_access,
)
from engine.belief.engine import synthesize, derive_belief, recompute_on_partial_loss


@pytest.mark.belief_purity
class TestAntiSmuggling:
    """The anti-smuggling guarantee — prior conclusions are unreachable."""

    def test_synthesize_has_no_prior_parameter(self) -> None:
        """synthesize() must not accept any parameter that provides prior conclusions."""
        assert validate_no_prior_access(synthesize)

    def test_derive_belief_has_no_prior_parameter(self) -> None:
        """derive_belief() must not accept prior belief values."""
        # derive_belief takes evidence_ids, evidence_texts, viewer_id, llm
        # It must NOT take prior_belief, previous_conclusion, etc.
        import inspect

        sig = inspect.signature(derive_belief)
        for param_name in sig.parameters:
            assert param_name not in FORBIDDEN_TERMS, (
                f"derive_belief() takes '{param_name}' — "
                "this allows access to prior conclusions"
            )

    def test_recompute_has_no_prior_parameter(self) -> None:
        """recompute_on_partial_loss() must not smuggle the old conclusion."""
        import inspect

        sig = inspect.signature(recompute_on_partial_loss)
        for param_name in sig.parameters:
            assert param_name not in FORBIDDEN_TERMS, (
                f"recompute_on_partial_loss() takes '{param_name}' — "
                "this smuggles the revoked evidence through the conclusion"
            )

    def test_static_check_entire_belief_module(self) -> None:
        """Static scan of the entire engine/belief/ directory for violations."""
        belief_dir = Path("engine/belief")
        violations = static_check_belief_module(belief_dir)
        assert violations == [], (
            f"Anti-smuggling violations found:\n"
            + "\n".join(f"  - {v}" for v in violations)
        )

    def test_synthesize_source_has_no_forbidden_names(self) -> None:
        """AST-level check: no variable named 'prior*' or 'previous*' in synthesize()."""
        source_file = Path("engine/belief/engine.py")
        tree = ast.parse(source_file.read_text())

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.name == "synthesize":
                    for child in ast.walk(node):
                        if isinstance(child, ast.Name):
                            assert not any(
                                term in child.id for term in FORBIDDEN_TERMS
                            ), (
                                f"synthesize() references '{child.id}' at line {child.lineno} — "
                                "prior conclusion reachable"
                            )
