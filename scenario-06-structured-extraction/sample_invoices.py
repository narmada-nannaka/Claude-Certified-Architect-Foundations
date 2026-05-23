"""Sample invoice text fixtures simulating extracted OCR.

Different fixtures exercise different concepts:
- clean: clear extraction, all high-confidence fields
- ambiguous_date: date format requires interpretation (US vs European)
- smudged_total: total isn't directly readable; must be derived from line items
- partial: missing optional fields (no PO, no tax breakdown)
- invalid_math: line items don't sum to declared total (validation will catch)
- novel_category: expense type doesn't fit standard categories ('other' pattern)
- multi_currency_ambiguous: $ symbol but country is Canada — USD or CAD?
"""

SAMPLE_INVOICES = {
    "clean": """
INVOICE
Acme Office Supplies
123 Main Street
Springfield, IL 62701

Invoice #: INV-2024-0847
Date: 2024-03-15
Due Date: 2024-04-14

Bill To:
Tech Corp
500 Innovation Drive

Line Items:
1. Premium Notebooks (50 units @ $4.50 ea) ..... $225.00
2. Ballpoint Pens (200 units @ $0.75 ea) ......  $150.00
3. Sticky Notes (100 pads @ $2.00 ea) ..........  $200.00

Subtotal:                                        $575.00
Tax (8%):                                         $46.00
TOTAL:                                           $621.00

Payment Terms: Net 30
Currency: USD
""",

    "ambiguous_date": """
INVOICE — Quick Supplies LLC

Number: QS-9921
Invoice Date: 03/04/2024
Due: 04/03/2024

Items:
- Cleaning supplies bulk (1) ........... 89.50
- Trash bags case (3 @ 12.00) .......... 36.00

Total: $125.50

US-based vendor
""",

    "smudged_total": """
INVOICE
Restaurant Equipment Wholesale
Order Date: 2024-02-28

Number: REW-447821

Line Items:
1. Commercial mixer (1 @ $1,250.00) ........ $1,250.00
2. Stainless prep table (2 @ $385.00) ......   $770.00
3. Knife set (1 @ $189.00) ..................  $189.00
4. Cutting boards (10 @ $24.50) .............  $245.00

Subtotal: $2,454.00
Tax (6.5%): $159.51
TOTAL: $2,6[smudged]

Currency: USD
Net 30
""",

    "partial": """
RECEIPT
City Cafe
Date: 2024-03-20

1x Coffee .............. $4.50
1x Sandwich ............ $11.00
1x Cookie ..............  $2.50

Total: $18.00

Thank you!
""",

    "invalid_math": """
INVOICE
Tech Distributors Inc.
Invoice: TD-2024-3301
Date: 2024-03-10
Due: 2024-04-09

Items:
1. Cat 6 cable bulk (5 boxes @ $85.00) ..... $425.00
2. RJ45 connectors (500 @ $0.15) ............  $75.00
3. Cable testers (2 @ $120.00) .............. $240.00

Subtotal: $740.00
Tax (7%): $51.80
TOTAL: $850.00

Net 30, USD
""",

    "novel_category": """
INVOICE
Wellness Together
Date: 2024-03-22
Inv #: WT-1147

Service: Team-building retreat
- Half-day facilitation .......... $1,800.00
- Materials and refreshments ......  $245.00
- Activity supplies ...............  $180.00

Subtotal: $2,225.00
Tax: $156.75
TOTAL: $2,381.75

USD
Net 15
""",

    "multi_currency_ambiguous": """
INVOICE
North Maple Trading
Toronto, ON

Number: NM-552
Date: March 18, 2024

Items:
1. Industrial fasteners (kg) (50 @ $8.00) .. $400.00
2. Specialty bolts (200 @ $1.25) ...........  $250.00

Total: $650.00

Net 30
"""
}


def get_invoice(name: str) -> str:
    """Get a sample invoice by name."""
    if name not in SAMPLE_INVOICES:
        raise ValueError(f"Unknown invoice: {name}. Available: {list(SAMPLE_INVOICES)}")
    return SAMPLE_INVOICES[name].strip()


def list_invoices() -> list[str]:
    return list(SAMPLE_INVOICES.keys())