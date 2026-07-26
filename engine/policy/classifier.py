"""Policy engine — Build #3: the inference ladder.

Freshness is inferred, not asked (REQ-12.0).
The inference ladder does as much work as possible before
requiring an explicit declaration from the user.

Four rungs:
1. SOURCE TYPE: Gmail is always evidence. Done.
2. SCHEMA SHAPE: A CRM deal record has different freshness than a CRM note.
3. DRIFT DETECTION: Was this cell edited this week? → live-state.
4. USER DECLARATION: The escape hatch for the ~10 items that need it.

Three freshness pipelines:
- IMMUTABLE: append-only → extract once, never re-check
- SLOW: slow-state → periodic re-extraction, cache-valid for hours
- LIVE: live-state → always live-read, never cache (no_live_values constraint)
"""

from __future__ import annotations

from core.enums import CostOfStaleness, SourceClass, VolatilityClass
from core.freshness_table import FreshnessEntry, get_freshness_default
from libs.observability.logging import get_logger

logger = get_logger("policy.classifier")


async def classify_freshness(
    provider_type: str,
    artifact_type: str,
    schema_hints: dict[str, str] | None = None,
    user_declaration: FreshnessEntry | None = None,
) -> FreshnessEntry:
    """Classify an artifact's freshness using the inference ladder.

    Rung 1: Source type defaults (from the freshness table)
    Rung 2: Schema-shape refinement
    Rung 3: Drift detection (future — needs historical data)
    Rung 4: User declaration (overrides all)
    """
    # Rung 4: User declaration overrides everything
    if user_declaration is not None:
        logger.info(
            "freshness_user_declared",
            provider=provider_type,
            artifact=artifact_type,
        )
        return user_declaration

    # Rung 1: Source type defaults
    default = get_freshness_default(provider_type, artifact_type)
    if default is not None:
        logger.debug(
            "freshness_from_table",
            provider=provider_type,
            artifact=artifact_type,
            volatility=default.volatility_class.value,
        )
        return default

    # Rung 2: Schema-shape inference
    if schema_hints:
        inferred = _infer_from_schema(provider_type, artifact_type, schema_hints)
        if inferred:
            logger.info(
                "freshness_inferred_from_schema",
                provider=provider_type,
                artifact=artifact_type,
            )
            return inferred

    # Fallback: conservative defaults
    logger.warning(
        "freshness_fallback",
        provider=provider_type,
        artifact=artifact_type,
    )
    return FreshnessEntry(
        provider_type=provider_type,
        artifact_type=artifact_type,
        volatility_class=VolatilityClass.SLOW_STATE,
        cost_of_staleness=CostOfStaleness.MEDIUM,
        source_class=SourceClass.EVIDENCE,
        notes="Fallback — no specific classification",
    )


def _infer_from_schema(
    provider_type: str,
    artifact_type: str,
    schema_hints: dict[str, str],
) -> FreshnessEntry | None:
    """Infer freshness from schema shape.

    Examples:
    - has_updated_at field + update frequency > weekly → live_state
    - has_created_at but no updated_at → append_only
    - is_archived or is_completed field → frozen
    """
    if schema_hints.get("is_immutable") == "true":
        return FreshnessEntry(
            provider_type=provider_type,
            artifact_type=artifact_type,
            volatility_class=VolatilityClass.FROZEN,
            cost_of_staleness=CostOfStaleness.LOW,
            source_class=SourceClass.AUTHORITY,
            notes="Inferred: immutable from schema",
        )

    if schema_hints.get("has_updated_at") == "true" and schema_hints.get("update_frequency") == "frequent":
        return FreshnessEntry(
            provider_type=provider_type,
            artifact_type=artifact_type,
            volatility_class=VolatilityClass.LIVE_STATE,
            cost_of_staleness=CostOfStaleness.HIGH,
            source_class=SourceClass.AUTHORITY,
            notes="Inferred: frequently updated from schema",
        )

    return None


def get_pipeline(entry: FreshnessEntry) -> str:
    """Route an artifact to the correct freshness pipeline.

    - IMMUTABLE: extract once, never re-check
    - SLOW: periodic re-extraction
    - LIVE: always live-read, never cache
    """
    if entry.volatility_class == VolatilityClass.FROZEN:
        return "immutable"
    elif entry.volatility_class == VolatilityClass.APPEND_ONLY:
        return "immutable"
    elif entry.volatility_class == VolatilityClass.SLOW_STATE:
        return "slow"
    elif entry.volatility_class == VolatilityClass.LIVE_STATE:
        return "live"
    else:
        return "slow"
