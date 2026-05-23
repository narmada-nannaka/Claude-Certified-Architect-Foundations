"""Scenario 6: Structured Data Extraction Pipeline.

Demonstrates Domain 4 concepts:
- Schema design (required/optional/nullable, 'other' + detail)
- Validation-retry with structured error feedback
- Confidence calibration and human review routing
- Multi-instance extraction with agreement signals
- Message Batches API mechanics (simulated)
- Information provenance
"""
import hashlib
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

from anthropic import Anthropic
from dotenv import load_dotenv

from sample_invoices import get_invoice, list_invoices
from extraction_schemas import EXTRACTION_TOOL_SCHEMA

load_dotenv()

# Terminal colors
RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
RED = "\033[31m"
CYAN = "\033[36m"
BLUE = "\033[34m"

OUTPUT_DIR = Path(__file__).parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

MODEL = "claude-opus-4-20250514"  # latest available; adjust to what's accessible to you


# ============================================================================
# CORE EXTRACTION
# ============================================================================

EXTRACTION_PROMPT = """You are an invoice extraction system. Extract structured data from the invoice text below.

Follow these rules:
1. Use the `submit_invoice_extraction` tool to return your results.
2. Required fields MUST be present. Nullable fields use null when unextractable.
3. Optional fields are omitted when not present in the source.
4. For dates, convert to ISO 8601 (YYYY-MM-DD). Use vendor country context to resolve ambiguous formats.
5. For currency, use the vendor's country to disambiguate dollar signs (Canadian vendor + $ → CAD).
6. For line items, extract every item with description, quantity, and unit_price as separate fields.
7. For expense_category, choose the best fit from the enum. Use "other" only when no category applies, and provide expense_category_detail.

CONFIDENCE CALIBRATION:
- "high": field is clearly visible and unambiguous in the source
- "medium": field is visible but interpretation was required (format conversion, multiple plausible readings)
- "low": field is partially obscured, calculated indirectly, or genuinely ambiguous
- When in doubt about confidence, choose the LOWER level. Over-confidence on uncertain fields causes downstream errors.

INVOICE TEXT:
{invoice_text}
"""


def get_client() -> Anthropic:
    """Get an Anthropic client, verifying API key is set."""
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print(f"{RED}ANTHROPIC_API_KEY not set in environment.{RESET}")
        sys.exit(1)
    return Anthropic()


def call_extraction(client: Anthropic, invoice_text: str, retry_feedback: str = None) -> dict:
    """Single extraction call. Returns the parsed tool input."""
    messages = [{"role": "user", "content": EXTRACTION_PROMPT.format(invoice_text=invoice_text)}]

    if retry_feedback:
        messages[0]["content"] += f"\n\nPREVIOUS ATTEMPT HAD ERRORS. Please correct:\n{retry_feedback}"

    response = client.messages.create(
        model=MODEL,
        max_tokens=2000,
        messages=messages,
        tools=[EXTRACTION_TOOL_SCHEMA],
        tool_choice={"type": "tool", "name": "submit_invoice_extraction"}
    )

    for block in response.content:
        if block.type == "tool_use" and block.name == "submit_invoice_extraction":
            return block.input

    raise RuntimeError("Model did not call the extraction tool")


# ============================================================================
# VALIDATION (Task 4.7)
# ============================================================================

def validate_extraction(extraction: dict) -> list[str]:
    """Apply business-rule validation beyond schema constraints.

    These checks catch semantic errors the schema can't:
    - Date format validity
    - Line items summing to total
    - Currency-symbol consistency
    - Required-when-other constraints
    """
    errors = []

    # Date format check
    invoice_date = extraction.get("invoice_date")
    if invoice_date is not None:
        try:
            parsed = datetime.strptime(invoice_date, "%Y-%m-%d")
            if parsed.year < 2000 or parsed.year > 2100:
                errors.append(
                    f"invoice_date '{invoice_date}' has implausible year. "
                    f"Verify the date extraction."
                )
        except ValueError:
            errors.append(
                f"invoice_date '{invoice_date}' is not a valid ISO 8601 date "
                f"(YYYY-MM-DD)."
            )

    # Line items sum to total (with tax tolerance)
    line_items = extraction.get("line_items", [])
    if line_items:
        line_total = sum(
            item.get("quantity", 0) * item.get("unit_price", 0)
            for item in line_items
        )
        declared_total = extraction.get("total_amount", 0)
        tax = extraction.get("tax_amount", 0)
        expected = line_total + tax

        if abs(expected - declared_total) > 0.10:  # 10-cent tolerance for rounding
            errors.append(
                f"Sum of line items ({line_total:.2f}) plus tax ({tax:.2f}) "
                f"= {expected:.2f}, but declared total is {declared_total:.2f}. "
                f"These should match within rounding tolerance. Recheck the "
                f"line items or the total."
            )

    # 'other' category requires detail
    if extraction.get("expense_category") == "other":
        detail = extraction.get("expense_category_detail")
        if not detail or len(detail.strip()) < 2:
            errors.append(
                "expense_category is 'other' but expense_category_detail is "
                "missing or too short. Provide a 2-4 word label."
            )

    # Required confidence fields
    confidences = extraction.get("field_confidences", {})
    required_conf_fields = ["vendor_name", "invoice_date", "total_amount", "currency"]
    for field in required_conf_fields:
        if field not in confidences:
            errors.append(f"field_confidences missing required field '{field}'.")
        elif confidences[field] not in ("high", "medium", "low"):
            errors.append(
                f"field_confidences['{field}'] = '{confidences[field]}' is not "
                f"a valid level (must be high/medium/low)."
            )

    return errors


def extract_with_retry(client: Anthropic, invoice_text: str, max_retries: int = 3) -> tuple[dict, list[dict]]:
    """Extract with validation-retry loop. Returns (extraction, retry_history)."""
    retry_history = []
    feedback = None

    for attempt in range(max_retries):
        extraction = call_extraction(client, invoice_text, retry_feedback=feedback)
        errors = validate_extraction(extraction)

        retry_history.append({
            "attempt": attempt + 1,
            "errors": errors,
            "extraction_preview": {
                "total_amount": extraction.get("total_amount"),
                "currency": extraction.get("currency"),
            }
        })

        if not errors:
            return extraction, retry_history

        # Build feedback for the next attempt
        feedback = "\n".join(f"- {e}" for e in errors)
        print(f"  {YELLOW}Attempt {attempt + 1}: validation errors, retrying...{RESET}")
        for e in errors:
            print(f"    {DIM}- {e}{RESET}")

    # Exhausted retries; return last extraction with the unresolved errors
    return extraction, retry_history


# ============================================================================
# CONFIDENCE-BASED ROUTING (Task 4.8)
# ============================================================================

def route_by_confidence(extraction: dict) -> str:
    """Decide where to send this extraction based on confidence calibration."""
    confidences = extraction.get("field_confidences", {})
    levels = list(confidences.values())

    if not levels:
        return "human_review"  # No confidence data → can't trust

    if all(c == "high" for c in levels):
        return "auto_process"

    if any(c == "low" for c in levels):
        return "human_review"

    return "auto_process_with_audit"


def routing_explanation(route: str) -> str:
    """Human-readable explanation of what each route means."""
    return {
        "auto_process": (
            f"{GREEN}AUTO PROCESS{RESET} — all critical fields high confidence. "
            f"Send directly to accounting."
        ),
        "auto_process_with_audit": (
            f"{YELLOW}AUTO PROCESS WITH AUDIT{RESET} — some fields medium "
            f"confidence. Flag for sampling-based review but don't block."
        ),
        "human_review": (
            f"{RED}HUMAN REVIEW{RESET} — low confidence on at least one critical "
            f"field. Queue for human verification before processing."
        ),
    }.get(route, "UNKNOWN")


# ============================================================================
# PROVENANCE (Task 5.6 extension)
# ============================================================================

def build_provenance_record(invoice_text: str, extraction: dict, retry_history: list[dict]) -> dict:
    """Build the full audit-trail record for the extraction."""
    return {
        "extracted_at": datetime.utcnow().isoformat() + "Z",
        "model": MODEL,
        "source_hash": hashlib.sha256(invoice_text.encode()).hexdigest()[:16],
        "extraction": extraction,
        "validation_history": retry_history,
        "routing_decision": route_by_confidence(extraction),
    }


def save_provenance_record(record: dict, name: str):
    """Save a provenance record to output/ with a timestamp."""
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    path = OUTPUT_DIR / f"{name}-{timestamp}.json"
    path.write_text(json.dumps(record, indent=2), encoding="utf-8")
    return path


# ============================================================================
# DISPLAY
# ============================================================================

def display_extraction(extraction: dict):
    """Pretty-print an extraction result."""
    print(f"\n{BOLD}Extraction:{RESET}")
    print(f"  Vendor:       {extraction.get('vendor_name')}")
    print(f"  Date:         {extraction.get('invoice_date')}")
    print(f"  Number:       {extraction.get('invoice_number')}")
    print(f"  Total:        {extraction.get('total_amount')} {extraction.get('currency')}")
    print(f"  Category:     {extraction.get('expense_category')}", end="")
    if extraction.get("expense_category") == "other":
        print(f" ({extraction.get('expense_category_detail', 'NO DETAIL')})", end="")
    print()

    line_items = extraction.get("line_items", [])
    if line_items:
        print(f"  Line items:")
        for item in line_items:
            print(f"    - {item.get('description')}: "
                  f"{item.get('quantity')} @ {item.get('unit_price')}")

    confidences = extraction.get("field_confidences", {})
    if confidences:
        print(f"  {BOLD}Field confidences:{RESET}")
        for field, conf in confidences.items():
            color = {"high": GREEN, "medium": YELLOW, "low": RED}.get(conf, "")
            print(f"    {field}: {color}{conf}{RESET}")

    notes = extraction.get("uncertainty_notes", "")
    if notes:
        print(f"  {DIM}Notes: {notes}{RESET}")


# ============================================================================
# MODE 1: Single extraction (basic schema in action)
# ============================================================================

def mode_single_extraction():
    """Concept 1: schema design with required/optional/nullable fields."""
    print(f"\n{BOLD}{CYAN}Mode 1: Single Extraction{RESET}")
    print(f"{DIM}Demonstrates schema design — required, optional, nullable fields.{RESET}\n")

    invoice_name = "clean"
    print(f"Extracting invoice: {BOLD}{invoice_name}{RESET}")
    invoice_text = get_invoice(invoice_name)

    client = get_client()
    extraction = call_extraction(client, invoice_text)

    display_extraction(extraction)

    # Show which optional fields were present vs omitted
    print(f"\n{BOLD}Field-type analysis:{RESET}")
    optional_fields = ["vendor_address", "purchase_order_number", "payment_terms",
                       "tax_amount", "subtotal", "expense_category_detail"]
    for field in optional_fields:
        if field in extraction:
            print(f"  {field}: {GREEN}present{RESET} = {extraction[field]}")
        else:
            print(f"  {field}: {DIM}omitted (not present in source){RESET}")

    nullable_fields = ["invoice_date", "invoice_number"]
    for field in nullable_fields:
        value = extraction.get(field)
        if value is None:
            print(f"  {field}: {YELLOW}null (model considered, found nothing){RESET}")
        else:
            print(f"  {field}: {GREEN}{value}{RESET}")

    record = build_provenance_record(invoice_text, extraction, [])
    path = save_provenance_record(record, "mode1-single")
    print(f"\n{DIM}Provenance saved: {path.name}{RESET}")


# ============================================================================
# MODE 2: Validation-retry loop (Task 4.7)
# ============================================================================

def mode_validation_retry():
    """Concept 3: structured error feedback drives convergence."""
    print(f"\n{BOLD}{CYAN}Mode 2: Validation-Retry Loop{RESET}")
    print(f"{DIM}Demonstrates structured error feedback enabling convergent retry.{RESET}\n")

    # Use the invalid_math invoice — line items don't sum to declared total
    invoice_name = "invalid_math"
    print(f"Extracting invoice: {BOLD}{invoice_name}{RESET}")
    print(f"{DIM}Note: this invoice has a math error baked in. Sum of line items{RESET}")
    print(f"{DIM}plus tax should be 791.80, but declared total is 850.00.{RESET}")
    print(f"{DIM}The model will likely report the declared total, then validation{RESET}")
    print(f"{DIM}will flag the mismatch and the retry loop will try to reconcile.{RESET}\n")

    invoice_text = get_invoice(invoice_name)
    client = get_client()

    extraction, retry_history = extract_with_retry(client, invoice_text, max_retries=3)

    display_extraction(extraction)

    print(f"\n{BOLD}Retry history:{RESET}")
    for entry in retry_history:
        attempt = entry["attempt"]
        err_count = len(entry["errors"])
        if err_count == 0:
            print(f"  Attempt {attempt}: {GREEN}succeeded{RESET}")
        else:
            print(f"  Attempt {attempt}: {YELLOW}{err_count} validation error(s){RESET}")
            for e in entry["errors"]:
                print(f"    {DIM}- {e[:100]}...{RESET}" if len(e) > 100 else f"    {DIM}- {e}{RESET}")

    record = build_provenance_record(invoice_text, extraction, retry_history)
    path = save_provenance_record(record, "mode2-retry")
    print(f"\n{DIM}Provenance saved: {path.name}{RESET}")


# ============================================================================
# MODE 3: Confidence-based routing (Task 4.8)
# ============================================================================

def mode_confidence_routing():
    """Concept 5: surface uncertainty, route by confidence."""
    print(f"\n{BOLD}{CYAN}Mode 3: Confidence-Based Routing{RESET}")
    print(f"{DIM}Demonstrates per-field confidence and routing by uncertainty.{RESET}\n")

    # Extract three invoices with different uncertainty profiles
    test_invoices = ["clean", "smudged_total", "multi_currency_ambiguous"]
    client = get_client()

    results = []
    for name in test_invoices:
        print(f"Extracting: {BOLD}{name}{RESET}...")
        invoice_text = get_invoice(name)
        extraction = call_extraction(client, invoice_text)
        route = route_by_confidence(extraction)
        results.append((name, extraction, route))

    print(f"\n{BOLD}Routing decisions:{RESET}\n")
    for name, extraction, route in results:
        print(f"{BOLD}{name}{RESET}")
        confidences = extraction.get("field_confidences", {})
        for field, conf in confidences.items():
            color = {"high": GREEN, "medium": YELLOW, "low": RED}.get(conf, "")
            print(f"  {field}: {color}{conf}{RESET}")

        notes = extraction.get("uncertainty_notes", "")
        if notes:
            print(f"  {DIM}Notes: {notes}{RESET}")

        print(f"  → {routing_explanation(route)}")
        print()


# ============================================================================
# MODE 4: Multi-instance extraction (Task 4.6 extended)
# ============================================================================

def mode_multi_instance():
    """Concept 6: agreement vs disagreement signal for critical extractions."""
    print(f"\n{BOLD}{CYAN}Mode 4: Multi-Instance Extraction{RESET}")
    print(f"{DIM}Two independent extractions of the same source. Agreement is signal.{RESET}\n")

    invoice_name = "ambiguous_date"
    print(f"Extracting: {BOLD}{invoice_name}{RESET} (two independent runs)")
    print(f"{DIM}The date format 03/04/2024 is ambiguous between US and European.{RESET}")
    print(f"{DIM}Independent runs may resolve it differently — disagreement is{RESET}")
    print(f"{DIM}the signal that human review is needed.{RESET}\n")

    invoice_text = get_invoice(invoice_name)
    client = get_client()

    print(f"  {DIM}Running extraction 1...{RESET}")
    extraction_1 = call_extraction(client, invoice_text)
    print(f"  {DIM}Running extraction 2...{RESET}")
    extraction_2 = call_extraction(client, invoice_text)

    print(f"\n{BOLD}Comparison:{RESET}\n")
    critical_fields = ["vendor_name", "invoice_date", "invoice_number",
                       "total_amount", "currency"]

    agreements = []
    disagreements = []

    for field in critical_fields:
        v1 = extraction_1.get(field)
        v2 = extraction_2.get(field)
        if v1 == v2:
            agreements.append((field, v1))
            print(f"  {field}: {GREEN}AGREE{RESET}  {v1}")
        else:
            disagreements.append((field, v1, v2))
            print(f"  {field}: {RED}DISAGREE{RESET}  Run 1: {v1}  |  Run 2: {v2}")

    print(f"\n{BOLD}Signal:{RESET}")
    if not disagreements:
        print(f"  {GREEN}All critical fields agree across both runs.{RESET}")
        print(f"  Higher reliability than single-instance.")
    else:
        print(f"  {RED}{len(disagreements)} critical field(s) disagree.{RESET}")
        print(f"  Human review required — model is uncertain across runs.")


# ============================================================================
# MODE 5: Simulated batch with custom_id (Task 4.5)
# ============================================================================

def mode_batch_simulation():
    """Concept 4: Message Batches API mechanics — custom_id correlation.

    This is a SIMULATION of the batch API pattern, run synchronously
    so it completes in this session. Real batch API would submit the
    requests, return a batch ID, and you'd poll for completion.
    """
    print(f"\n{BOLD}{CYAN}Mode 5: Batch Processing Simulation{RESET}")
    print(f"{DIM}Demonstrates custom_id correlation pattern. (Run synchronously{RESET}")
    print(f"{DIM}for this demo; real batch API would submit and poll.){RESET}\n")

    # Simulate a batch of invoices, each with a custom_id
    batch = []
    for i, name in enumerate(["clean", "ambiguous_date", "smudged_total", "partial"], 1):
        batch.append({
            "custom_id": f"invoice-{i:03d}-{name}",
            "invoice_name": name,
        })

    print(f"{BOLD}Submitting batch of {len(batch)} invoices...{RESET}\n")

    client = get_client()
    results = []
    failures = []

    for item in batch:
        print(f"  Processing {item['custom_id']}...")
        try:
            invoice_text = get_invoice(item["invoice_name"])
            extraction = call_extraction(client, invoice_text)
            results.append({
                "custom_id": item["custom_id"],
                "status": "succeeded",
                "extraction": extraction,
            })
        except Exception as e:
            failures.append({
                "custom_id": item["custom_id"],
                "status": "failed",
                "error": str(e),
            })

    print(f"\n{BOLD}Batch results:{RESET}")
    print(f"  Total submitted: {len(batch)}")
    print(f"  {GREEN}Succeeded:{RESET} {len(results)}")
    print(f"  {RED}Failed:{RESET}    {len(failures)}")

    print(f"\n{BOLD}Correlation by custom_id:{RESET}")
    for r in results:
        cid = r["custom_id"]
        e = r["extraction"]
        print(f"  {cid}")
        print(f"    → Vendor: {e.get('vendor_name')}, Total: {e.get('total_amount')} {e.get('currency')}")

    if failures:
        print(f"\n{BOLD}{YELLOW}Failures (to resubmit by custom_id):{RESET}")
        for f in failures:
            print(f"  {f['custom_id']}: {f['error']}")

    # Save the batch result file
    batch_record = {
        "batch_id": f"sim-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
        "submitted_count": len(batch),
        "results": results,
        "failures": failures,
    }
    path = OUTPUT_DIR / f"batch-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
    path.write_text(json.dumps(batch_record, indent=2), encoding="utf-8")
    print(f"\n{DIM}Batch record saved: {path.name}{RESET}")


# ============================================================================
# MAIN MENU
# ============================================================================

def main():
    while True:
        print(f"\n{BOLD}Scenario 6: Structured Data Extraction{RESET}")
        print(f"  1. Single extraction (schema design: required/optional/nullable)")
        print(f"  2. Validation-retry loop (structured error feedback)")
        print(f"  3. Confidence-based routing (calibration → human review)")
        print(f"  4. Multi-instance extraction (agreement as signal)")
        print(f"  5. Batch simulation (custom_id correlation)")
        print(f"  q. Quit")

        choice = input(f"\n{BOLD}Choice:{RESET} ").strip().lower()

        try:
            if choice == "1":
                mode_single_extraction()
            elif choice == "2":
                mode_validation_retry()
            elif choice == "3":
                mode_confidence_routing()
            elif choice == "4":
                mode_multi_instance()
            elif choice == "5":
                mode_batch_simulation()
            elif choice in ("q", "quit", "exit"):
                print("Bye.")
                break
            else:
                print(f"{RED}Unknown choice: {choice}{RESET}")
        except KeyboardInterrupt:
            print(f"\n{YELLOW}Interrupted.{RESET}")
        except Exception as e:
            print(f"{RED}Error: {e}{RESET}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    main()