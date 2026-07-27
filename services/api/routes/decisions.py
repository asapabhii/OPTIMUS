"""Decisions surface (Surface 4) — entity resolution decisions, real data."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

from services.api.routes.ingest import get_entity_store

router = APIRouter()


class ERDecision(BaseModel):
    decision_id: str
    entity_a_name: str
    entity_b_name: str
    entity_type: str
    similarity: float
    status: str  # "pending" | "merged" | "rejected"
    sources: list[str]
    created_at: str
    evidence: dict[str, Any] | None = None


class DecisionQueue(BaseModel):
    decisions: list[ERDecision]
    total_pending: int
    total_resolved: int


# In-memory decision store (resolved decisions)
_decision_store: list[ERDecision] = []
_resolved_ids: set[str] = set()

# Higher threshold — only surface pairs that genuinely look like duplicates
ER_SURFACE_THRESHOLD = 0.65
ER_AUTO_MERGE_THRESHOLD = 0.92


def _compare_entities(name_a: str, name_b: str, type_a: str, props_a: dict, props_b: dict) -> tuple[float, dict[str, Any]]:
    """Compare two entities using the same logic as the Splink resolver."""
    try:
        from rapidfuzz import fuzz
    except ImportError:
        return 0.0, {}

    norm_a = name_a.lower().strip()
    norm_b = name_b.lower().strip()

    if not norm_a or not norm_b:
        return 0.0, {}

    if norm_a == norm_b:
        return 1.0, {"reason": "Exact name match", "token_sort": 100, "ratio": 100, "wratio": 100}

    # Strip legal suffixes
    suffixes = [
        " inc", " inc.", " corp", " corp.", " corporation", " company",
        " co.", " co", " llc", " ltd", " ltd.", " limited",
        " ag", " gmbh", " plc", " pty", " sa", " srl",
    ]
    for s in suffixes:
        if norm_a.endswith(s):
            norm_a = norm_a[: -len(s)].strip()
        if norm_b.endswith(s):
            norm_b = norm_b[: -len(s)].strip()

    if norm_a == norm_b:
        return 0.97, {"reason": "Same entity, differ only on legal suffix", "token_sort": 100, "ratio": 95, "wratio": 100}

    # Strip common parenthetical qualifiers before comparing
    import re
    paren_re = re.compile(r"\s*\(.*?\)\s*")
    clean_a = paren_re.sub("", norm_a).strip()
    clean_b = paren_re.sub("", norm_b).strip()

    # If stripping parens makes them identical, it's just a qualifier difference
    if clean_a and clean_b and clean_a == clean_b:
        return 0.97, {"reason": "Same name, differ only on qualifier", "token_sort": 100, "ratio": 95, "wratio": 100}

    # Use cleaned names for comparison if qualifiers inflated similarity
    compare_a = clean_a if clean_a else norm_a
    compare_b = clean_b if clean_b else norm_b

    # Fuzzy scores
    token_sort = fuzz.token_sort_ratio(compare_a, compare_b) / 100.0
    ratio = fuzz.ratio(compare_a, compare_b) / 100.0
    wratio = fuzz.WRatio(compare_a, compare_b) / 100.0

    fuzzy_score = (token_sort * 0.40) + (wratio * 0.30) + (ratio * 0.30)

    # Key-token penalty
    tokens_a = set(re.findall(r"[a-z]+|\d+", compare_a))
    tokens_b = set(re.findall(r"[a-z]+|\d+", compare_b))
    diff_tokens = tokens_a.symmetric_difference(tokens_b)
    penalties: list[str] = []

    if diff_tokens and fuzzy_score > 0.60:
        has_numeric_diff = any(t.isdigit() for t in diff_tokens)
        has_short_word_diff = any(len(t) <= 4 and not t.isdigit() for t in diff_tokens)

        if has_numeric_diff:
            fuzzy_score *= 0.70
            penalties.append(f"Numeric difference: {diff_tokens}")
        elif has_short_word_diff:
            fuzzy_score *= 0.80
            penalties.append(f"Key word difference: {diff_tokens}")

    # Person-name penalty: if first OR last name is completely different, heavy penalty
    words_a = compare_a.split()
    words_b = compare_b.split()
    if len(words_a) >= 2 and len(words_b) >= 2 and fuzzy_score > 0.60:
        first_sim = fuzz.ratio(words_a[0], words_b[0]) / 100.0
        last_sim = fuzz.ratio(words_a[-1], words_b[-1]) / 100.0
        if first_sim < 0.70 or last_sim < 0.70:
            fuzzy_score *= 0.50
            penalties.append(f"Different names: '{words_a[0]}' vs '{words_b[0]}', '{words_a[-1]}' vs '{words_b[-1]}'")
        elif first_sim < 0.95 or last_sim < 0.95:
            fuzzy_score *= 0.75
            penalties.append("Partial name difference")

    # Domain match bonus
    attr_bonus = 0.0
    domain_a = props_a.get("domain", "")
    domain_b = props_b.get("domain", "")
    if domain_a and domain_b and domain_a == domain_b:
        attr_bonus += 0.15

    email_a = props_a.get("email", "")
    email_b = props_b.get("email", "")
    if email_a and email_b and email_a == email_b:
        attr_bonus += 0.20

    final_score = min(fuzzy_score + attr_bonus, 0.99)

    # Build evidence
    evidence: dict[str, Any] = {
        "name_a_normalized": norm_a,
        "name_b_normalized": norm_b,
        "token_sort": round(token_sort * 100, 1),
        "ratio": round(ratio * 100, 1),
        "wratio": round(wratio * 100, 1),
        "fuzzy_combined": round(fuzzy_score * 100, 1),
        "attr_bonus": round(attr_bonus * 100, 1),
        "final_score": round(final_score * 100, 1),
    }

    # Build human-readable reason
    reasons: list[str] = []
    if token_sort > 0.80:
        reasons.append(f"Strong token overlap ({token_sort:.0%})")
    if wratio > 0.85:
        reasons.append(f"High character similarity ({wratio:.0%})")
    if attr_bonus > 0:
        if domain_a == domain_b:
            reasons.append(f"Same domain: {domain_a}")
        if email_a == email_b:
            reasons.append(f"Same email: {email_a}")
    if penalties:
        reasons.extend(penalties)

    evidence["reason"] = "; ".join(reasons) if reasons else f"Moderate similarity ({final_score:.0%})"
    evidence["penalties"] = penalties

    return round(final_score, 4), evidence


def _detect_potential_duplicates() -> list[ERDecision]:
    """Detect potential duplicate entities using the tuned comparison."""
    store = get_entity_store()
    if len(store) < 2:
        return []

    ER_TYPES = {"person", "company", "deal"}

    by_type: dict[str, list] = {}
    for e in store:
        if e.type in ER_TYPES:
            by_type.setdefault(e.type, []).append(e)

    new_decisions: list[ERDecision] = []
    seen_pairs: set[tuple[str, str]] = set()

    for entity_type, entities in by_type.items():
        for i in range(len(entities)):
            for j in range(i + 1, min(i + 50, len(entities))):
                a, b = entities[i], entities[j]
                pair_key = tuple(sorted([a.id, b.id]))
                if pair_key in seen_pairs:
                    continue
                seen_pairs.add(pair_key)

                decision_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"{a.id}:{b.id}"))

                # Skip already-resolved
                if decision_id in _resolved_ids:
                    continue

                score, evidence = _compare_entities(
                    a.name, b.name, entity_type,
                    a.properties, b.properties,
                )

                if score >= ER_SURFACE_THRESHOLD:
                    decision = ERDecision(
                        decision_id=decision_id,
                        entity_a_name=a.name,
                        entity_b_name=b.name,
                        entity_type=entity_type,
                        similarity=round(score, 3),
                        status="merged" if score >= ER_AUTO_MERGE_THRESHOLD else "pending",
                        sources=list({a.source, b.source}),
                        created_at=datetime.utcnow().isoformat(),
                        evidence=evidence,
                    )
                    new_decisions.append(decision)

    return new_decisions


@router.get("/decisions", response_model=DecisionQueue)
async def list_decisions(
    viewer_id: uuid.UUID = uuid.UUID("00000000-0000-0000-0000-000000000001"),
    status: str | None = None,
) -> DecisionQueue:
    """List entity resolution decisions — detected from real ingested data."""
    detected = _detect_potential_duplicates()
    # Only include user-resolved decisions from store, not auto-detected ones
    user_resolved = [d for d in _decision_store if d.status in ("merged", "rejected")]
    all_decisions = detected + user_resolved

    pending = sum(1 for d in all_decisions if d.status == "pending")
    resolved = sum(1 for d in all_decisions if d.status in ("merged", "rejected"))

    if status:
        filtered = [d for d in all_decisions if d.status == status]
    else:
        # Default: only show pending (decisions needing human review)
        # Auto-merges are silent — they don't need the user's attention
        filtered = [d for d in all_decisions if d.status == "pending"]

    return DecisionQueue(
        decisions=filtered,
        total_pending=pending,
        total_resolved=resolved,
    )


@router.post("/decisions/{decision_id}/resolve")
async def resolve_decision(
    decision_id: str,
    action: str = "merge",
) -> dict:
    """Resolve an ER decision."""
    _resolved_ids.add(decision_id)

    for d in _decision_store:
        if d.decision_id == decision_id:
            d.status = "merged" if action == "merge" else "rejected"
            return {"status": "ok", "decision_id": decision_id, "action": action}

    _decision_store.append(ERDecision(
        decision_id=decision_id,
        entity_a_name="",
        entity_b_name="",
        entity_type="",
        similarity=0.0,
        status="merged" if action == "merge" else "rejected",
        sources=[],
        created_at=datetime.utcnow().isoformat(),
    ))

    return {"status": "ok", "decision_id": decision_id, "action": action}
