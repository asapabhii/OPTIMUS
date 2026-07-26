"""J0: 4-step demo script with Meridian Supply Co.

Step 1: Connect (Nango OAuth) — user connects HubSpot, Google Sheets, Gmail
Step 2: Watch (fast-path) — visible graph build as entities are resolved
Step 3: Discover conflict — "When does the Meridian renewal close?"
         → CRM says Feb 1, spreadsheet says Jan 15
         → Answer envelope shows both values, which won, and why
Step 4: Decide — user accepts the spreadsheet's date or overrides
         → Decision logged, reversible, becomes a pending proposal

The demo takes <5 minutes and demonstrates:
- Entity resolution (3 names → 1 entity)
- Conflict surfacing (renewal date disagement)
- Answer envelope (citations, freshness, layer, arbitration rule)
- Decision log (visible, reversible)
"""

DEMO_STEPS = [
    {
        "step": 1,
        "title": "Connect Your Tools",
        "action": "Connect HubSpot, Google Sheets, and Gmail via Nango OAuth",
        "expected_time": "60 seconds",
        "what_happens": [
            "Nango handles OAuth for each tool",
            "Fast-path ingestion starts immediately for most-recent 50 items",
            "User sees a progress indicator",
        ],
    },
    {
        "step": 2,
        "title": "Watch the Graph Build",
        "action": "Observe the entity graph as entities are resolved in real time",
        "expected_time": "90 seconds",
        "what_happens": [
            "Entities appear as they are extracted: Meridian Supply, contacts, deals",
            "Three CRM variants resolve to one entity (auto-merged, logged)",
            "David Chen and Dave Chen resolve to one person",
            "SKU variants resolve (IND-5500, IND-5500-A)",
            "Graph visualization updates live",
        ],
    },
    {
        "step": 3,
        "title": "Discover a Conflict",
        "action": 'Ask: "When does the Meridian renewal close?"',
        "expected_time": "5 seconds",
        "what_happens": [
            "Retrieval planner identifies Meridian Supply entity",
            "Fan-out: CRM deal (Feb 1) + spreadsheet (Jan 15) + email context",
            "Conflict detected between CRM and spreadsheet",
            "Answer envelope shows:",
            '  → "The renewal closes January 15, 2026."',
            '  → Conflict block: CRM says Feb 1, spreadsheet says Jan 15',
            '  → Arbitration: "Showing the spreadsheet — it is your declared SoR',
            '     for renewals — last edited 6 days ago; the CRM figure may be stale."',
            "  → Inline citation for each claim with freshness indicator",
            "  → Promotion prompt: Would you like to declare which date is correct?",
        ],
    },
    {
        "step": 4,
        "title": "Make a Decision",
        "action": "Accept the spreadsheet date or override with the CRM date",
        "expected_time": "10 seconds",
        "what_happens": [
            "User clicks to accept the spreadsheet's Jan 15 date",
            "Decision logged as an AutoDecision (type: resolution_rule_applied)",
            "Decision is visible in the Decisions surface",
            "Decision is reversible in one click",
            "A pending proposal is stored for the Phase 3 approval queue",
        ],
    },
]
