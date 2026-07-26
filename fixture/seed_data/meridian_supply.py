"""J0: Meridian Supply Co. fixture data.

A synthetic company with deliberately embedded conflicts to demonstrate
every product capability from demo minute one.

Data:
- 3 CRM name variants for the same entity: "Meridian Supply", "Meridian Supply Co.", "Meridian Supply Company"
- Conflicting renewal dates: spreadsheet says Jan 15, CRM says Feb 1
- A pricing exception in an email thread (evidence, not authority)
- Non-person entities: SKUs, projects
"""

from __future__ import annotations

# CRM records (HubSpot-shaped) — 3 name variants for the same entity
CRM_COMPANIES = [
    {
        "id": "crm-001",
        "name": "Meridian Supply",
        "domain": "meridiansupply.com",
        "industry": "Industrial Distribution",
        "annual_revenue": 45_000_000,
        "owner": "sarah.chen@example.com",
    },
    {
        "id": "crm-002",
        "name": "Meridian Supply Co.",
        "domain": "meridiansupply.com",
        "industry": "Industrial Distribution",
        "annual_revenue": 45_000_000,
        "owner": "james.park@example.com",
    },
    {
        "id": "crm-003",
        "name": "Meridian Supply Company",
        "domain": "meridiansupplyco.com",
        "industry": "Manufacturing & Distribution",
        "annual_revenue": 48_000_000,
        "owner": "sarah.chen@example.com",
    },
]

# CRM deals — note the conflicting renewal date vs spreadsheet
CRM_DEALS = [
    {
        "id": "deal-001",
        "company_id": "crm-001",
        "name": "Meridian Supply - Enterprise Renewal 2026",
        "amount": 180_000,
        "stage": "Contract Sent",
        "close_date": "2026-02-01",  # CRM says Feb 1
        "owner": "sarah.chen@example.com",
    },
]

# Spreadsheet data — the renewal date here differs from CRM
SPREADSHEET_RENEWALS = [
    {
        "row": 12,
        "company": "Meridian Supply",
        "renewal_date": "2026-01-15",  # Spreadsheet says Jan 15
        "contract_value": 180_000,
        "tier": "Enterprise",
        "notes": "Multi-year, negotiated pricing",
        "last_edited": "2026-07-20",
    },
]

# Email thread — pricing exception (evidence, not authority)
EMAIL_THREAD = [
    {
        "id": "email-001",
        "subject": "Re: Meridian Supply pricing discussion",
        "from": "vp_sales@example.com",
        "to": "account_exec@example.com",
        "date": "2026-06-15",
        "body": (
            "For Meridian, we agreed to a 15% discount on the enterprise tier "
            "for the first year of the renewal. This is an exception — do NOT "
            "update the standard pricing sheet."
        ),
    },
    {
        "id": "email-002",
        "subject": "Re: Re: Meridian Supply pricing discussion",
        "from": "account_exec@example.com",
        "to": "vp_sales@example.com",
        "date": "2026-06-16",
        "body": "Understood, I'll note this in the deal but keep standard pricing in the sheet.",
    },
]

# Non-person entities: SKUs and projects
PRODUCT_SKUS = [
    {"sku": "IND-5500", "name": "Industrial Valve Assembly 5500", "price": 450.00},
    {"sku": "IND-5500-A", "name": "Industrial Valve Assembly 5500 (Rev A)", "price": 475.00},
    {"sku": "IND-5500-B", "name": "Valve Assembly 5500B", "price": 475.00},
]

PROJECTS = [
    {
        "id": "proj-001",
        "name": "Meridian Q3 Onboarding",
        "status": "In Progress",
        "owner": "cs_lead@example.com",
    },
]

# CRM contacts
CRM_CONTACTS = [
    {
        "id": "contact-001",
        "name": "David Chen",
        "email": "d.chen@meridiansupply.com",
        "title": "VP Procurement",
        "company_id": "crm-001",
    },
    {
        "id": "contact-002",
        "name": "Dave Chen",
        "email": "dchen@meridiansupply.com",
        "title": "VP, Procurement",
        "company_id": "crm-002",
    },
]
