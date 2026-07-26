"""G14: The freshness table — per connector × artifact type.

One-day decision that de-risks the policy engine before a line of it is coded.
The declaration pass overrides ~10 items; the rest are inferred defaults.

Two axes, modeled separately (P5):
- Volatility: WHEN to refresh
- Cost-of-staleness: WHETHER answering from cache is permitted
"""

from __future__ import annotations

from dataclasses import dataclass

from core.enums import CostOfStaleness, SourceClass, VolatilityClass


@dataclass(frozen=True)
class FreshnessEntry:
    """Default freshness classification for a connector × artifact type."""

    provider_type: str
    artifact_type: str
    volatility_class: VolatilityClass
    cost_of_staleness: CostOfStaleness
    source_class: SourceClass
    notes: str = ""


# ─────────────────────────────────────────────────────────────
# THE TABLE — the policy engine's starting point
# ─────────────────────────────────────────────────────────────

FRESHNESS_TABLE: list[FreshnessEntry] = [
    # === HubSpot (CRM — authority for deal/account data) ===
    FreshnessEntry("hubspot", "deal", VolatilityClass.LIVE_STATE, CostOfStaleness.CRITICAL, SourceClass.AUTHORITY,
                   "Deal stage changes without announcement; walking into a renewal on stale data is the wedge pain"),
    FreshnessEntry("hubspot", "contact", VolatilityClass.SLOW_STATE, CostOfStaleness.MEDIUM, SourceClass.AUTHORITY,
                   "Contact info changes deliberately; a few times per year"),
    FreshnessEntry("hubspot", "company", VolatilityClass.SLOW_STATE, CostOfStaleness.MEDIUM, SourceClass.AUTHORITY,
                   "Company info is slow-moving"),
    FreshnessEntry("hubspot", "note", VolatilityClass.APPEND_ONLY, CostOfStaleness.LOW, SourceClass.EVIDENCE,
                   "CRM notes are evidence, not authority"),
    FreshnessEntry("hubspot", "activity", VolatilityClass.APPEND_ONLY, CostOfStaleness.LOW, SourceClass.EVIDENCE,
                   "Logged activities are append-only events"),

    # === Google Sheets (the differentiator — spreadsheet as SoR) ===
    FreshnessEntry("google_sheets", "cell_value", VolatilityClass.LIVE_STATE, CostOfStaleness.CRITICAL, SourceClass.AUTHORITY,
                   "A cell in a declared-SoR sheet is live state; the renewal date that differs is this exact cell"),
    FreshnessEntry("google_sheets", "sheet_structure", VolatilityClass.SLOW_STATE, CostOfStaleness.LOW, SourceClass.AUTHORITY,
                   "Headers and structure change rarely"),

    # === Google Drive (documents) ===
    FreshnessEntry("google_drive", "document", VolatilityClass.SLOW_STATE, CostOfStaleness.MEDIUM, SourceClass.AUTHORITY,
                   "Living docs change deliberately"),
    FreshnessEntry("google_drive", "presentation", VolatilityClass.FROZEN, CostOfStaleness.LOW, SourceClass.AUTHORITY,
                   "Completed decks are frozen artifacts — the 8-month-old figure in the demo"),
    FreshnessEntry("google_drive", "pdf", VolatilityClass.FROZEN, CostOfStaleness.LOW, SourceClass.AUTHORITY,
                   "PDFs are generally frozen"),

    # === Gmail (evidence, never authority — REQ-3.2) ===
    FreshnessEntry("gmail", "email", VolatilityClass.APPEND_ONLY, CostOfStaleness.LOW, SourceClass.EVIDENCE,
                   "Email is append-only evidence. May inform — never assert."),

    # === Slack (evidence) ===
    FreshnessEntry("slack", "message", VolatilityClass.APPEND_ONLY, CostOfStaleness.LOW, SourceClass.EVIDENCE,
                   "Chat is evidence (REQ-3.2). A brainstorm saying 'maybe drop the enterprise tier' "
                   "must be structurally incapable of conflicting with canonical pricing."),

    # === Gong / Fireflies (call transcripts — evidence) ===
    FreshnessEntry("gong", "transcript", VolatilityClass.APPEND_ONLY, CostOfStaleness.LOW, SourceClass.EVIDENCE,
                   "Call transcripts are append-only evidence"),
    FreshnessEntry("fireflies", "transcript", VolatilityClass.APPEND_ONLY, CostOfStaleness.LOW, SourceClass.EVIDENCE,
                   "Call transcripts are append-only evidence"),

    # === Notion ===
    FreshnessEntry("notion", "page", VolatilityClass.SLOW_STATE, CostOfStaleness.MEDIUM, SourceClass.AUTHORITY,
                   "Wiki pages change deliberately"),
    FreshnessEntry("notion", "database", VolatilityClass.SLOW_STATE, CostOfStaleness.MEDIUM, SourceClass.AUTHORITY,
                   "Notion databases are slow-state structured data"),

    # === Jira ===
    FreshnessEntry("jira", "issue", VolatilityClass.LIVE_STATE, CostOfStaleness.MEDIUM, SourceClass.AUTHORITY,
                   "Issue status changes without announcement"),
    FreshnessEntry("jira", "comment", VolatilityClass.APPEND_ONLY, CostOfStaleness.LOW, SourceClass.EVIDENCE,
                   "Comments are evidence"),

    # === Salesforce ===
    FreshnessEntry("salesforce", "opportunity", VolatilityClass.LIVE_STATE, CostOfStaleness.CRITICAL, SourceClass.AUTHORITY,
                   "Same as HubSpot deals — live state, critical staleness"),
    FreshnessEntry("salesforce", "account", VolatilityClass.SLOW_STATE, CostOfStaleness.MEDIUM, SourceClass.AUTHORITY),
    FreshnessEntry("salesforce", "contact", VolatilityClass.SLOW_STATE, CostOfStaleness.MEDIUM, SourceClass.AUTHORITY),
]


def get_freshness_default(
    provider_type: str, artifact_type: str
) -> FreshnessEntry | None:
    """Look up the default freshness classification for a connector × artifact type."""
    for entry in FRESHNESS_TABLE:
        if entry.provider_type == provider_type and entry.artifact_type == artifact_type:
            return entry
    return None


def get_provider_defaults(provider_type: str) -> list[FreshnessEntry]:
    """Get all freshness defaults for a provider."""
    return [e for e in FRESHNESS_TABLE if e.provider_type == provider_type]
