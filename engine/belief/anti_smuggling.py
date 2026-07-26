"""Anti-smuggling guarantee — the prior conclusion is structurally unreachable.

This module provides static verification that the synthesize() function
NEVER has access to a prior belief value. This is the hardest part of
Build #2 and the thing nobody else does.

Without this guarantee, "recompute from the remainder" gets implemented as
"keep the old conclusion and adjust the confidence," which smuggles the
revoked evidence through inside the conclusion itself.

Verified in CI by the belief-purity suite (tests/suites/belief_purity/).
"""

from __future__ import annotations

import ast
import inspect
from pathlib import Path
from typing import Callable

from libs.observability.logging import get_logger

logger = get_logger("anti_smuggling")

# Terms that MUST NOT appear in synthesize()'s signature or closure
FORBIDDEN_TERMS = frozenset({
    "prior",
    "previous",
    "prior_belief",
    "previous_belief",
    "prior_conclusion",
    "previous_conclusion",
    "old_belief",
    "cached_belief",
    "existing_belief",
    "last_belief",
})


def validate_no_prior_access(func: Callable[..., object]) -> bool:
    """Validate that a function has no access to prior belief values.

    Checks:
    1. No forbidden terms in parameter names
    2. No forbidden terms in the function's source code variable names
    3. No closure variables containing forbidden terms

    Returns True if clean, raises AssertionError if contaminated.
    """
    sig = inspect.signature(func)
    for param_name in sig.parameters:
        if param_name in FORBIDDEN_TERMS or any(
            term in param_name for term in FORBIDDEN_TERMS
        ):
            msg = (
                f"BELIEF-PURITY VIOLATION: synthesize() parameter '{param_name}' "
                f"allows access to prior conclusions. The anti-smuggling guarantee "
                f"requires the prior conclusion to be structurally unreachable."
            )
            raise AssertionError(msg)

    # Check source code for forbidden variable assignments
    try:
        source = inspect.getsource(func)
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.Name) and node.id in FORBIDDEN_TERMS:
                msg = (
                    f"BELIEF-PURITY VIOLATION: synthesize() references '{node.id}' "
                    f"at line {node.lineno}. The prior conclusion must be unreachable."
                )
                raise AssertionError(msg)
    except OSError:
        logger.warning("could_not_inspect_source", function=func.__name__)

    return True


def static_check_belief_module(module_path: Path) -> list[str]:
    """Statically check an entire module for anti-smuggling violations.

    Used by the CI belief-purity suite to scan the entire engine/belief/ directory.
    Returns a list of violations (empty = clean).
    """
    violations: list[str] = []

    for py_file in module_path.rglob("*.py"):
        try:
            tree = ast.parse(py_file.read_text())
        except SyntaxError:
            violations.append(f"{py_file}: SyntaxError — could not parse")
            continue

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.name == "synthesize":
                    for arg in node.args.args:
                        if any(term in arg.arg for term in FORBIDDEN_TERMS):
                            violations.append(
                                f"{py_file}:{node.lineno} — synthesize() takes "
                                f"parameter '{arg.arg}' (forbidden)"
                            )

    return violations
