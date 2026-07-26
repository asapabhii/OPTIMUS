"""Evidence-class bar enforcement (REQ-6.9b, P7).

A brainstorm thread saying "maybe drop the enterprise tier"
must be structurally incapable of conflicting with canonical pricing.

Evidence may inform — never assert.
Evidence sources are BARRED from generating incremental promotion proposals.
This is enforced at THREE levels:
1. Pydantic model validator (core/models/proposal.py)
2. Database CHECK constraint (migration 006)
3. This runtime check (belt-and-suspenders)
"""

from __future__ import annotations

from core.enums import SourceClass
from libs.observability.logging import get_logger

logger = get_logger("canon.evidence_class_bar")


class EvidenceClassBarViolation(Exception):
    """Raised when an evidence-class source attempts to generate a proposal."""

    pass


def enforce_evidence_class_bar(source_class: SourceClass, action: str = "proposal") -> None:
    """Enforce the evidence-class bar.

    Raises EvidenceClassBarViolation if source_class is EVIDENCE.
    """
    if source_class == SourceClass.EVIDENCE:
        msg = (
            f"Evidence-class sources cannot generate {action}. "
            "Chat, call, email, and brainstorm content may inform — never assert. "
            "(REQ-6.9b, P7)"
        )
        logger.error("evidence_class_bar_violation", action=action)
        raise EvidenceClassBarViolation(msg)
