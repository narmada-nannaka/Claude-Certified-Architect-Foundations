"""Schema definitions for structured invoice extraction.

Demonstrates exam-tested patterns:
- Required vs optional vs nullable fields (Task 4.4)
- "other" + detail pattern for extensible categorization (Task 4.4)
- Per-field confidence calibration (Task 4.8)
"""

# The main extraction tool the model calls to submit results
EXTRACTION_TOOL_SCHEMA = {
    "name": "submit_invoice_extraction",
    "description": (
        "Submit the structured extraction for an invoice. Required fields "
        "MUST be present; optional fields may be omitted; nullable fields "
        "(those with 'null' in their type) must be present but may be null "
        "when not extractable from the source."
    ),
    "input_schema": {
        "type": "object",
        "required": [
            "vendor_name",       # required — downstream needs vendor
            "invoice_date",      # required, nullable — accounting needs date but may be unreadable
            "invoice_number",    # required, nullable — usually present but sometimes missing
            "total_amount",      # required — every invoice has a total
            "currency",          # required — payment processing depends on this
            "line_items",        # required — must be present, can be empty array
            "expense_category",  # required — for downstream routing
            "field_confidences", # required — calibration is mandatory
        ],
        "properties": {
            "vendor_name": {
                "type": "string",
                "description": "The vendor (seller) name as it appears on the invoice."
            },
            "vendor_address": {
                # OPTIONAL — many receipts don't have a full address
                "type": "string",
                "description": "Vendor's full address if present. Omit this field if not present."
            },
            "invoice_date": {
                # NULLABLE — must explicitly acknowledge presence, even when unreadable
                "type": ["string", "null"],
                "description": (
                    "Invoice date in ISO 8601 format (YYYY-MM-DD). "
                    "Return null if the date is unreadable or absent. "
                    "For ambiguous formats like 03/04/2024, use context "
                    "(US vendor → MM/DD/YYYY, European vendor → DD/MM/YYYY)."
                )
            },
            "invoice_number": {
                "type": ["string", "null"],
                "description": "The invoice or receipt number. Return null if absent."
            },
            "purchase_order_number": {
                # OPTIONAL — B2B usually has PO, retail doesn't
                "type": "string",
                "description": "Purchase order number if present on the invoice. Omit if not present."
            },
            "total_amount": {
                "type": "number",
                "description": (
                    "Grand total in the stated currency, as a decimal number. "
                    "Example: 1247.50, not '$1,247.50'."
                )
            },
            "currency": {
                "type": "string",
                "enum": ["USD", "EUR", "GBP", "JPY", "CAD", "AUD", "OTHER"],
                "description": (
                    "Currency code. For ambiguous symbols like '$', use vendor "
                    "country to disambiguate (Canadian vendor + '$' → CAD)."
                )
            },
            "tax_amount": {
                "type": "number",
                "description": "Total tax amount on the invoice. Omit if no tax line is shown."
            },
            "subtotal": {
                "type": "number",
                "description": "Subtotal before tax. Omit if not shown separately."
            },
            "line_items": {
                "type": "array",
                "description": "Itemized list. Empty array if invoice has no itemization.",
                "items": {
                    "type": "object",
                    "required": ["description", "quantity", "unit_price"],
                    "properties": {
                        "description": {"type": "string"},
                        "quantity": {"type": "number"},
                        "unit_price": {"type": "number"}
                    }
                }
            },
            "payment_terms": {
                # OPTIONAL
                "type": "string",
                "description": "Payment terms like 'Net 30'. Omit if not specified."
            },
            "expense_category": {
                "type": "string",
                "enum": [
                    "office_supplies",
                    "travel",
                    "meals",
                    "equipment",
                    "professional_fees",
                    "utilities",
                    "subscriptions",
                    "other"
                ],
                "description": (
                    "Best-fit category. Use 'other' if no category fits well — "
                    "expense_category_detail then becomes required."
                )
            },
            "expense_category_detail": {
                # REQUIRED when expense_category is 'other'
                "type": "string",
                "description": (
                    "REQUIRED when expense_category is 'other'. A 2-4 word "
                    "label describing the expense type (e.g., 'team_building', "
                    "'certification_fee', 'donation'). Used to identify "
                    "patterns that might become new enum values."
                )
            },
            "field_confidences": {
                "type": "object",
                "required": ["vendor_name", "invoice_date", "total_amount", "currency"],
                "description": (
                    "Confidence labels for the critical fields. high = clearly "
                    "visible and unambiguous. medium = visible but interpretation "
                    "required. low = partially obscured, calculated indirectly, "
                    "or ambiguous. WHEN IN DOUBT, CHOOSE THE LOWER LEVEL."
                ),
                "properties": {
                    "vendor_name": {"type": "string", "enum": ["high", "medium", "low"]},
                    "invoice_date": {"type": "string", "enum": ["high", "medium", "low"]},
                    "total_amount": {"type": "string", "enum": ["high", "medium", "low"]},
                    "currency": {"type": "string", "enum": ["high", "medium", "low"]}
                }
            },
            "uncertainty_notes": {
                "type": "string",
                "description": (
                    "Brief notes (1-2 sentences) about anything ambiguous, "
                    "smudged, or requiring interpretation in the source. Empty "
                    "string if extraction was straightforward."
                )
            }
        }
    }
}