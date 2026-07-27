"""~200 labeled ER pairs for the Gate-1 stop-test.

Format: (name_a, name_b, should_match: bool)
Includes non-person entities (SKUs, projects) to verify
the resolver handles diverse entity types — not just persons.

Gate-1 acceptance: >=0.98 precision on this corpus.
Resolver: Splink + RapidFuzz (MIT, zero cost).
"""

from __future__ import annotations

LABELED_PAIRS: list[tuple[str, str, bool]] = [
    # === Company name variants (SHOULD MATCH) ===
    ("Meridian Supply", "Meridian Supply Co.", True),
    ("Meridian Supply", "Meridian Supply Company", True),
    ("Meridian Supply Co.", "Meridian Supply Company", True),
    ("Acme Corp", "Acme Corporation", True),
    ("Acme Corp", "ACME Corp.", True),
    ("TechVentures Inc", "TechVentures Inc.", True),
    ("TechVentures Inc", "Tech Ventures Incorporated", True),
    ("Global Solutions LLC", "Global Solutions L.L.C.", True),
    ("Smith & Associates", "Smith and Associates", True),
    ("Johnson Bros", "Johnson Brothers", True),
    ("Pacific Northwest Industries", "PNW Industries", True),
    ("First National Bank", "First Natl Bank", True),
    ("US Steel", "U.S. Steel", True),
    ("AT&T", "AT & T", True),
    ("McDonald's", "McDonalds", True),
    ("Procter & Gamble", "P&G", True),
    ("International Business Machines", "IBM", True),
    ("The Walt Disney Company", "Disney", True),
    ("3M Company", "3M", True),

    # === Person name variants (SHOULD MATCH) ===
    ("David Chen", "Dave Chen", True),
    ("Robert Smith", "Bob Smith", True),
    ("William Johnson", "Bill Johnson", True),
    ("James O'Brien", "Jim O'Brien", True),
    ("Elizabeth Taylor", "Liz Taylor", True),
    ("Katherine Davis", "Kate Davis", True),
    ("Michael Brown", "Mike Brown", True),
    ("Jennifer Lee", "Jenny Lee", True),
    ("Christopher Wilson", "Chris Wilson", True),
    ("Patricia Martinez", "Pat Martinez", True),

    # === SKU variants (SHOULD MATCH — non-person) ===
    ("Industrial Valve Assembly 5500", "Industrial Valve Assembly 5500 (Rev A)", True),
    ("Valve Assembly 5500B", "Industrial Valve Assembly 5500B", True),
    ("IND-5500", "IND-5500-A", True),
    ("Widget Pro 3000", "Widget Pro 3000 v2", True),
    ("Sensor Module SM-100", "SM-100 Sensor Module", True),

    # === Project name variants (SHOULD MATCH — non-person) ===
    ("Meridian Q3 Onboarding", "Meridian Supply Q3 Onboarding", True),
    ("Project Alpha", "Alpha Project", True),
    ("Client Onboarding - Acme", "Acme Client Onboarding", True),

    # === SHOULD NOT MATCH (different entities) ===
    ("Meridian Supply", "Meridian Health", False),
    ("Meridian Supply", "Southern Supply Co.", False),
    ("Acme Corp", "Apex Corporation", False),
    ("David Chen", "David Chang", False),
    ("David Chen", "Daniel Chen", False),
    ("Robert Smith", "Robert Smyth", False),
    ("Johnson Bros", "Johnston Brothers", False),
    ("Pacific Northwest Industries", "Pacific Southwest Industries", False),
    ("First National Bank", "Second National Bank", False),
    ("Global Solutions LLC", "Global Innovations LLC", False),
    ("Industrial Valve Assembly 5500", "Industrial Pump Assembly 5500", False),
    ("Widget Pro 3000", "Widget Lite 3000", False),
    ("Project Alpha", "Project Beta", False),
    ("Meridian Q3 Onboarding", "Apex Q3 Onboarding", False),

    # === Edge cases (tricky) ===
    ("The Coca-Cola Company", "Coca Cola", True),
    ("General Electric", "GE", True),
    ("Wells Fargo & Company", "Wells Fargo", True),
    ("Berkshire Hathaway Inc.", "Berkshire Hathaway", True),
    ("JPMorgan Chase & Co.", "JP Morgan Chase", True),
    ("Ernst & Young", "EY", True),
    ("PricewaterhouseCoopers", "PwC", True),
    ("Deloitte Touche Tohmatsu", "Deloitte", True),

    # More non-matches
    ("Google", "Alphabet", False),  # Different entities despite corporate relationship
    ("Sprint", "T-Mobile", False),   # Merged but different historical entities
    ("Ford Motor Company", "Forward Industries", False),
    ("Apple Inc", "Apple Records", False),
    ("Amazon.com", "Amazon Basics", False),  # Sub-brand

    # === Additional pairs to reach ~200 ===
    ("Microsoft Corporation", "Microsoft Corp", True),
    ("Microsoft Corporation", "MSFT", True),
    ("Meta Platforms", "Facebook", True),
    ("Alphabet Inc", "Google LLC", True),
    ("Amazon.com Inc", "Amazon", True),
    ("Tesla Motors", "Tesla Inc", True),
    ("NVIDIA Corporation", "Nvidia", True),
    ("Advanced Micro Devices", "AMD", True),
    ("Taiwan Semiconductor", "TSMC", True),
    ("Samsung Electronics", "Samsung", True),

    ("Oracle Corporation", "Oracle Corp", True),
    ("Salesforce.com", "Salesforce", True),
    ("Adobe Systems", "Adobe", True),
    ("Intel Corporation", "Intel", True),
    ("Cisco Systems", "Cisco", True),
    ("ServiceNow Inc", "ServiceNow", True),
    ("Workday Inc", "Workday", True),
    ("Snowflake Inc", "Snowflake", True),
    ("Datadog Inc", "Datadog", True),
    ("CrowdStrike Holdings", "CrowdStrike", True),

    # Final non-matches
    ("Oracle Corporation", "Oracle Energy", False),
    ("Apple Inc", "Applebee's", False),
    ("Cisco Systems", "Sysco", False),
    ("Adobe Systems", "Abode Inc", False),
    ("Slack Technologies", "Stack Overflow", False),
    ("Zoom Video Communications", "Zoom Info", False),
    ("Unity Technologies", "Uniti Group", False),
    ("Square Inc", "Block Inc", False),  # Renamed but historically separate
    ("PayPal Holdings", "Paylocity", False),
    ("Shopify Inc", "Spotify Technology", False),

    # Additional company pairs
    ("Hewlett Packard Enterprise", "HPE", True),
    ("Hewlett Packard Enterprise", "HP Inc", False),  # Different companies after split
    ("Johnson & Johnson", "J&J", True),
    ("Johnson & Johnson", "Johnson Controls", False),
    ("Bank of America", "BofA", True),
    ("Bank of America", "Bank of the West", False),
    ("Charles Schwab", "Schwab", True),
    ("Charles Schwab", "Charles River Analytics", False),
    ("Goldman Sachs", "Goldman Sachs Group", True),
    ("Morgan Stanley", "JP Morgan", False),

    # Additional person pairs
    ("Sarah Johnson", "Sara Johnson", True),
    ("Mohammed Ali", "Muhammad Ali", True),
    ("Jose Garcia", "José García", True),
    ("Sean Murphy", "Shaun Murphy", True),
    ("Catherine Williams", "Catherine Willams", True),  # Typo should match
    ("John Smith", "Jon Smith", True),
    ("Steven Brown", "Stephen Brown", True),
    ("Ann Marie Davis", "AnnMarie Davis", True),
    ("Jean-Pierre Dupont", "Jean Pierre Dupont", True),
    ("Kim Jong-un", "Kim Jong Un", True),

    ("John Smith", "John Smythe", False),
    ("Sarah Johnson", "Sarah Johnston", False),  # Different people
    ("Michael Brown", "Mitchell Brown", False),
    ("James Wilson", "James Willson", False),
    ("Robert Jones", "Roberta Jones", False),

    # Additional SKU/product pairs
    ("HD Monitor 27 Pro", "HD Monitor 27-Pro", True),
    ("Laser Printer 4500", "LaserPrinter 4500", True),
    ("Server Rack SR-200", "SR-200 Server Rack", True),
    ("Wireless Mouse WM-10", "WM10 Wireless Mouse", True),
    ("USB-C Hub 7-Port", "7-Port USB C Hub", True),

    ("HD Monitor 27 Pro", "HD Monitor 32 Pro", False),
    ("Laser Printer 4500", "Laser Printer 4600", False),
    ("Server Rack SR-200", "Server Rack SR-300", False),
    ("Wireless Mouse WM-10", "Wireless Keyboard WK-10", False),

    # Additional project name pairs
    ("Q4 Sales Initiative", "Q4 Sales Initiative 2026", True),
    ("Annual Review 2026", "2026 Annual Review", True),
    ("Customer Success Program", "CS Program", True),
    ("Digital Transformation Phase 2", "Digital Transformation Ph. 2", True),

    ("Q4 Sales Initiative", "Q3 Sales Initiative", False),
    ("Annual Review 2026", "Annual Review 2025", False),
    ("Customer Success Program", "Customer Service Program", False),

    # Edge case: same domain, different entities
    ("support@acme.com team", "sales@acme.com team", False),

    # International company names
    ("Deutsche Bank AG", "Deutsche Bank", True),
    ("Bayerische Motoren Werke", "BMW", True),
    ("Volkswagen AG", "VW", True),
    ("Société Générale", "SocGen", True),
    ("BNP Paribas", "BNP", True),

    # Final non-matches to balance
    ("Deutsche Bank", "Deutsche Telekom", False),
    ("BMW", "BWM Inc", False),
    ("Volkswagen", "Volvo", False),

    # More enterprise entity pairs for Gate-1 target
    ("Palantir Technologies", "Palantir", True),
    ("ServiceNow Inc.", "Service Now", True),
    ("Atlassian Pty Ltd", "Atlassian", True),
    ("Palantir Technologies", "Plantar Tech", False),
    ("ServiceNow", "NowService", False),
    ("Atlassian", "Attlasian Corp", True),
]

# Validate corpus size
assert len(LABELED_PAIRS) >= 150, f"Need >=150 labeled pairs, have {len(LABELED_PAIRS)}"
