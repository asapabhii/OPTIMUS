"""Domain enumerations — the vocabulary of the knowledge model.

Every enum here maps directly to the classification axes in the source documents:
- P5: volatility and cost-of-staleness, modeled separately
- P7: authorities vs. evidence
- REQ-5.8: visibility as an extensible level, not a boolean
"""

from __future__ import annotations

import enum


class VolatilityClass(str, enum.Enum):
    """How fast does the underlying truth drift? (P5)

    Determines WHEN to refresh.
    """

    LIVE_STATE = "live_state"        # Changes without announcement (inventory, balances, deal stage)
    SLOW_STATE = "slow_state"        # Changes deliberately, a few times/year (pricing, org chart)
    APPEND_ONLY = "append_only"      # Nothing changes retroactively (transcripts, emails, commits)
    FROZEN = "frozen"                # Immutable by definition (signed contracts, completed audits)


class CostOfStaleness(str, enum.Enum):
    """What breaks if this is wrong? (P5)

    Determines WHETHER answering from cache is permitted at all.
    Orthogonal to volatility — a slow fact can demand a live read
    if being wrong is expensive.
    """

    CRITICAL = "critical"    # Never answer from cache; live read mandatory
    HIGH = "high"            # Cache only if very fresh (< minutes)
    MEDIUM = "medium"        # Cache acceptable if within hours
    LOW = "low"              # Cache acceptable if within days


class SourceClass(str, enum.Enum):
    """Is this source an authority or evidence? (P7)

    Authorities: few, declared, carry policy — where you learn WHAT is true.
    Evidence: plentiful, append-only — where you learn WHY.

    Evidence may NEVER assert, and NEVER generates incremental promotion proposals (REQ-6.9b).
    """

    AUTHORITY = "authority"
    EVIDENCE = "evidence"


class VisibilityLevel(str, enum.Enum):
    """Extensible visibility level — two states now, modeled for three (REQ-5.8).

    READABLE: viewer can see content.
    NOT_READABLE: viewer cannot see content (no hints, no "there's more").
    DISCOVERABLE: [LATER, Gate 8] viewer told it exists, may request access.
    """

    READABLE = "readable"
    NOT_READABLE = "not_readable"
    # DISCOVERABLE = "discoverable"  # Gate 8 — when real cross-team sensitivity earns it


class ProvenanceType(str, enum.Enum):
    """How was this fact established? (P7, REQ-3.2b)

    Human authority is a FIRST-CLASS provenance type, not a fallback.
    """

    SOURCE_REF = "source_ref"            # Read from a source document/record
    HUMAN_AUTHORITY = "human_authority"   # Asserted by a human in a specific role


class DeclarationTypeEnum(str, enum.Enum):
    """Types of declarations stored in the canon-shaped schema (G3)."""

    SOR_DECLARATION = "sor_declaration"      # "HubSpot is the SoR for deal stage"
    RESOLUTION_RULE = "resolution_rule"      # "Acme = Acme Inc." (REQ-6.4)


class AutoDecisionType(str, enum.Enum):
    """Types of automatic decisions the system makes (REQ-8.2 stage 1)."""

    ENTITY_MERGE = "entity_merge"
    FRESHNESS_CLASSIFICATION = "freshness_classification"
    STORAGE_POLICY = "storage_policy"
    RESOLUTION_RULE_APPLIED = "resolution_rule_applied"


class SortOutcome(str, enum.Enum):
    """Three-way sort result for staged candidates (REQ-3.6a)."""

    NOVEL = "novel"                  # No existing match → auto-merge
    CONFIDENT_MATCH = "confident"    # Above threshold → auto-merge, logged, reversible
    CONFLICT = "conflict"            # Ambiguous or contradictory → escalate to review queue


class TaskClass(str, enum.Enum):
    """LLM task classes for model routing (P28).

    The routing table maps each class to a model tier.
    The CANON_MUTATION tier uses the APPROVED model only — no override.
    """

    CLASSIFICATION = "classification"       # Cheapest adequate (DeepSeek/Qwen-class)
    EXTRACTION = "extraction"               # Cheapest adequate
    RETRIEVAL_PLANNING = "retrieval_planning"  # Reliable mid-tier
    SYNTHESIS = "synthesis"                  # Most capable
    CANON_MUTATION = "canon_mutation"        # Approved model only — NO OVERRIDE (REQ-13.2)


class ModelTier(str, enum.Enum):
    """Model quality tiers bound to Portkey virtual keys (P28)."""

    CHEAPEST_ADEQUATE = "cheapest_adequate"
    MID_TIER = "mid_tier"
    MOST_CAPABLE = "most_capable"
    APPROVED_ONLY = "approved_only"  # Hard rule — confabulation here is corrupted org data
