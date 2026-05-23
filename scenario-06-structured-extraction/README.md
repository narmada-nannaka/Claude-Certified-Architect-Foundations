# Scenario 6: Structured Data Extraction

> A working invoice extraction pipeline that demonstrates every Domain 4
> concept through hands-on execution — covering the deepest content of
> Domain 4 (20% of the exam) plus extensions to Domain 5 information
> provenance for the **Claude Certified Architect – Foundations** exam.

---

## What this scenario teaches

How production systems use Claude to extract structured information
from unstructured input — invoices, receipts, contracts, medical
records — with calibrated confidence, validation-retry recovery,
batch processing, and audit trails.

| Domain | Weight | Coverage in this scenario |
|---|---|---|
| **Domain 4** — Prompt Engineering & Structured Output | 20% (deep) | Schemas, validation-retry, batch mechanics, confidence calibration |
| **Domain 5** — Context Management & Reliability | 15% (extension) | Information provenance, partial-failure recovery |

No new sample questions live in this scenario — all twelve published
sample questions are mapped across Scenarios 1-5. What Scenario 6
closes is the **task statement depth** in Domain 4 beyond the sample
question surface.

### Task statements deep-covered

| Task | What |
|---|---|
| **4.3** | Tool use with JSON schemas for guaranteed structured output |
| **4.4** | Schema design: required, optional, nullable fields, "other" + detail |
| **4.5** | Message Batches API mechanics — custom_id, 24-hour window, failures |
| **4.7** | Validation-retry loops with structured error feedback |
| **4.8** | Confidence calibration and human review routing |
| **5.6** | Information provenance through extraction pipeline |

---

## Three sentences to memorize

These complement Scenario 5's three to cover all of Domain 4.

> **1. Schema design encodes a contract: required for downstream
> essentials, optional for omitted-when-absent, nullable for "I
> considered this and it's not extractable." The "other" + detail
> pattern provides extensibility without sacrificing structure.**

> **2. Validation-retry loops succeed when error feedback is
> field-specific and rule-citing. Vague feedback produces vague retries;
> specific feedback enables convergence.**

> **3. Confidence calibration plus routing turns probabilistic
> extraction into a system: high confidence auto-processes, mixed
> confidence audits, low confidence routes to human review.
> Provenance preserves the uncertainty signal alongside the extracted
> value so failures can be investigated, not just detected.**

---

## Architecture at a glance

```
            ┌───────────────────────────────────┐
            │  Source document (image / text)   │
            └───────────┬───────────────────────┘
                        ▼
            ┌───────────────────────────────────┐
            │  pipeline.py (extraction runner)  │
            │  Modes:                           │
            │   1. Single extraction            │
            │   2. Validation-retry             │
            │   3. Confidence routing           │
            │   4. Multi-instance comparison    │
            │   5. Batch simulation             │
            └───────────┬───────────────────────┘
                        ▼
            ┌───────────────────────────────────┐
            │  Anthropic API (via SDK)          │
            │  - tool_use with JSON schema      │
            │  - extraction_tool_schema.py      │
            └───────────┬───────────────────────┘
                        ▼
            ┌───────────────────────────────────┐
            │  Tool input (structured JSON):    │
            │   - vendor_name, invoice_date     │
            │   - line_items, total, currency   │
            │   - expense_category + detail     │
            │   - field_confidences             │
            │   - uncertainty_notes             │
            └───────────┬───────────────────────┘
                        ▼
            ┌───────────────────────────────────┐
            │  Validation (business rules)      │
            │  - Date format validity           │
            │  - Line items sum to total        │
            │  - 'other' has detail             │
            │  - Confidence labels valid        │
            └───────────┬───────────────────────┘
                        ▼
              ┌─────────┴──────────┐
              ▼ (errors)            ▼ (no errors)
        ┌──────────────┐    ┌──────────────────────┐
        │ Retry with   │    │  Confidence routing  │
        │ structured   │    │   - all high → auto  │
        │ feedback     │    │   - mixed → audit    │
        │ (up to 3x)   │    │   - any low → human  │
        └──────────────┘    └──────┬───────────────┘
                                    ▼
                        ┌───────────────────────┐
                        │  Provenance record    │
                        │   - source_hash       │
                        │   - model, timestamp  │
                        │   - retry history     │
                        │   - routing decision  │
                        └───────────────────────┘
```

Five modes you can run; one unified architecture they all share.

---

## The six concepts in detail

### Concept 1: Schema design — required, optional, nullable (Task 4.4)

Three distinct field-type patterns in the extraction tool schema:

| Pattern | Behavior | When to use |
|---|---|---|
| **Required** | Must be present; schema validates | Downstream system genuinely needs it |
| **Optional** (omit from required) | Field omitted from output when absent | Contextual data; missing is normal |
| **Nullable** (required key, allowed null) | Field present but value is null | Need explicit "I considered this and it's absent" |

The `extraction_schemas.py` file demonstrates all three:
- `total_amount` is required (every invoice has one)
- `purchase_order_number` is optional (B2B usually has it, retail doesn't)
- `invoice_date` is nullable (downstream needs to know the date or know we couldn't read it)

### Concept 2: The "other" + detail pattern (Task 4.4)

For extensible categorization:

```python
"expense_category": {"enum": ["travel", "meals", ..., "other"]},
"expense_category_detail": {
    "description": "REQUIRED when expense_category is 'other'."
}
```

This handles the cases that don't fit your enum without losing
structure. Downstream you aggregate `other` entries by detail strings
to discover patterns that should become new enum values.

### Concept 3: Validation-retry with structured error feedback (Task 4.7)

JSON schemas enforce structure but not semantics. A date `"2024-13-45"`
is structurally a string but semantically invalid. The pipeline adds
business-rule validation:

- Date format check (must parse as ISO 8601)
- Line items sum to total (with rounding tolerance)
- Currency-symbol consistency
- 'other' category has detail
- Required confidence fields present

When validation fails, the retry feedback to the model is **specific**:

```
Sum of line items (740.00) plus tax (51.80) = 791.80, but
declared total is 850.00. These should match.
```

NOT:

```
The extraction was wrong. Please try again.
```

Structured feedback enables convergent retry; vague feedback doesn't.

### Concept 4: Message Batches API mechanics (Task 4.5)

The batch simulation in mode 5 demonstrates the `custom_id`
correlation pattern:

```python
batch_requests = [
    {"custom_id": "invoice-001-acme", "params": {...}},
    {"custom_id": "invoice-002-restaurant", "params": {...}},
    ...
]
```

When results come back, each carries the `custom_id` of the original
request. You match results to your data regardless of ordering, and
on partial failure you resubmit only the failed `custom_id`s — not
the entire batch.

The batch API trade-offs:
- 50% cost savings vs synchronous
- Up to 24-hour processing window, no SLA
- No multi-turn tool calling within a single request
- No streaming, no real-time observation
- Best for one-shot extraction at scale

### Concept 5: Confidence calibration and routing (Task 4.8)

The model labels each critical field's confidence:
- **high**: clearly visible and unambiguous
- **medium**: visible but interpretation required
- **low**: partially obscured, calculated indirectly, or ambiguous

Plus the calibration anchor in the prompt: *"When in doubt about
confidence, choose the LOWER level."*

Routing rules:
- All high → auto-process (send to accounting)
- Mixed high/medium → auto-process with audit
- Any low → human review queue

This gives you ~80% automation with ~20% human verification —
preserving system value at both ends.

### Concept 6: Information provenance (Task 5.6 ext)

Every extraction is saved with full audit trail:

```json
{
  "extracted_at": "2024-03-15T14:23:11Z",
  "model": "claude-opus-4-20250514",
  "source_hash": "sha256:abc...",
  "extraction": { ... },
  "validation_history": [
    {"attempt": 1, "errors": [...]},
    {"attempt": 2, "errors": []}
  ],
  "routing_decision": "human_review"
}
```

Months later, when accounting flags a discrepancy, the audit trail
tells you exactly what happened: which model, what version, what the
input was, how confidence was assessed, how many retry rounds, what
the routing decision was.

---

## Prerequisites

- Python 3.10+
- An Anthropic API key
- PowerShell (Windows) or bash (macOS/Linux)
- VS Code recommended

No external CI runners. No PowerShell-to-external-process complexity.
Pure Python calling the Anthropic SDK.

---

## Quick start

```powershell
cd scenario-06-structured-extraction

python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

copy .env.example .env
# Edit .env: ANTHROPIC_API_KEY=sk-ant-...

python pipeline.py
```

You'll see a menu with five modes. Run them in order to walk through
all six concepts.

---

## Project layout

```
scenario-06-structured-extraction/
├── README.md
├── pipeline.py                  # Main script with five modes
├── extraction_schemas.py        # JSON schema with all field patterns
├── sample_invoices.py           # Realistic invoice text fixtures
├── requirements.txt
├── .env.example
└── output/                      # Provenance records (created at runtime)
```

---

## The five modes — what to run, what to watch for

### Mode 1: Single extraction (basic schema patterns)

```
python pipeline.py
1
```

Extracts the `clean` invoice fixture. Watch:

- All required fields filled (vendor_name, total_amount, currency, line_items)
- Optional fields present because they're in the source (vendor_address, payment_terms)
- Nullable fields filled with real values (invoice_date) — not null

The script displays a "field-type analysis" showing which optional
fields were omitted vs present.

**To explore the patterns further**: change the invoice in code from
`"clean"` to `"partial"` (a coffee shop receipt). Optional fields get
omitted entirely; required fields are still produced.

### Mode 2: Validation-retry loop

```
python pipeline.py
2
```

Extracts the `invalid_math` fixture, where line items + tax don't
equal the declared total (740 + 52 = 792, but declared is 850).

Watch:

- First attempt likely reports the declared total (850) as-is
- Validation flags the mismatch with specific math
- Retry feedback explains: "Sum is 791.80 but declared is 850.00"
- Model converges — either revising line items or the total
- Retry history captured in the provenance record

### Mode 3: Confidence-based routing

```
python pipeline.py
3
```

Extracts three invoices with different uncertainty profiles:

| Invoice | Expected routing |
|---|---|
| `clean` | auto_process (all high confidence) |
| `smudged_total` | human_review (total is low confidence — smudged) |
| `multi_currency_ambiguous` | human_review or auto_process_with_audit (depends on whether Claude resolved the $ vs CAD question) |

Watch the confidence labels for each field and the routing decision
each invoice gets.

### Mode 4: Multi-instance extraction

```
python pipeline.py
4
```

Extracts the `ambiguous_date` invoice (date 03/04/2024 is ambiguous
between US and European interpretation) twice.

Watch:

- Each run independently extracts a date
- If both runs agree → reliability signal
- If they disagree → human review is needed (the model is uncertain
  across runs even though each run might report high confidence)

This demonstrates that agreement across independent runs is a stronger
signal than individual confidence.

### Mode 5: Batch simulation

```
python pipeline.py
5
```

Processes four invoices, each tagged with a `custom_id`:
- `invoice-001-clean`
- `invoice-002-ambiguous_date`
- `invoice-003-smudged_total`
- `invoice-004-partial`

Watch:

- Each result is correlated back by `custom_id`
- Failed extractions (if any) are identified by their `custom_id`
- The batch record file shows the complete correlation

In real batch usage, you'd submit to the actual Batches API, poll for
completion, and download results. The mechanics — `custom_id` per
request, results matched back, partial-failure handling — are
identical.

---

## What's in `output/` after running all modes

| File | What it contains |
|---|---|
| `mode1-single-<timestamp>.json` | Provenance for the single extraction |
| `mode2-retry-<timestamp>.json` | Provenance including the retry history |
| `batch-<timestamp>.json` | Batch result with `custom_id` correlation |

Open these and inspect:

- The `source_hash` (proves which input produced this output — different inputs produce different hashes)
- The `validation_history` (shows what was tried and corrected)
- The `routing_decision` (shows how the system would route this in production)

This IS information provenance — exam content under Task 5.6.

---

## Studying with this code

### 1. Read the schema first

`extraction_schemas.py` is the most exam-relevant file. Read through
it and trace which fields use which pattern (required / optional /
nullable / "other" + detail). The structure of this schema is the
structure the exam tests.

### 2. Modify the calibration anchor

The prompt in `pipeline.py` includes the line *"When in doubt about
confidence, choose the LOWER level."* Remove it temporarily and re-run
mode 3. You should see the model default to "high" confidence on more
fields — observing the effect of calibration anchoring in real output.

Restore the anchor before continuing.

### 3. Break the validation feedback

In `pipeline.py`'s `extract_with_retry` function, change the feedback
construction to be vague:

```python
feedback = "The extraction was wrong. Try again."
```

Re-run mode 2. The retry loop will likely not converge — the model
produces slight variations of the same wrong answer because it has no
specific information about what failed.

Restore the structured feedback. This is the experimental
demonstration of why Task 4.7 emphasizes structured error feedback.

### 4. Test the schema patterns

Edit `extraction_schemas.py` and:

- Move `vendor_address` from optional to required. Run mode 1 against
  the `partial` invoice (coffee receipt). The schema constraint will
  force the model to produce SOMETHING for vendor_address, even if
  it has to make it up.

- Change `invoice_date` from nullable to required. Run mode 1 against
  the `smudged_total` invoice (where the date isn't smudged). It still
  works, but if you fed it an invoice with no date, the schema would
  force a wrong value.

Restore the original patterns. These experiments show why the
required/optional/nullable distinction matters in practice.

---

## Common distractor patterns this code debunks

| Distractor | Why wrong | Reference |
|---|---|---|
| Make all fields required | Forces model to invent values when fields are absent | Concept 1 |
| Make all fields optional | Loses downstream guarantees and audit trail | Concept 1 |
| Make everything a free-text string | Loses structure, can't validate, can't route | Concept 2 |
| Schema is enough; no business validation | Catches structure, misses semantics (invalid dates, math errors) | Concept 3 |
| Generic "try again" retry feedback | Doesn't enable convergence; produces variations of the same error | Concept 3 |
| Send all extractions to human review | Defeats automation purpose | Concept 5 |
| Trust all extractions equally | Errors compound; downstream catches them weeks later | Concept 5 |
| Force model to label everything "high" confidence | Hides uncertainty; no routing signal | Concept 5 |
| Use batch for blocking workflows | 24-hour latency on workflow that needs seconds | Concept 4 |
| Use sync for everything to "avoid batch complexity" | Wastes 50% cost savings on workloads where time doesn't matter | Concept 4 |
| Skip multi-instance for legal/medical documents | High-stakes extraction needs reliability beyond single run | Mode 4 |
| Store just the extracted value, no metadata | Can't investigate failures weeks later | Concept 6 |

---

## The Domain 4 mental model in one paragraph

A production extraction system is built around four interacting layers.
The **schema** encodes the contract — required fields for downstream
essentials, optional fields that omit when absent, nullable fields
that explicitly acknowledge absence, the "other" + detail pattern for
extensibility. The **prompt** teaches the model the contract plus
calibration (confidence levels with the "when in doubt go lower"
anchor). The **validation** layer catches semantic errors the schema
can't (date formats, math consistency, business rules) and provides
structured field-specific feedback to enable convergent retry. The
**routing** layer uses the model's confidence labels to route by
reliability — high confidence auto-processes, low confidence goes to
human review, mixed gets audited. Underneath everything, the
**provenance** record preserves source hashes, retry history,
confidence signals, and routing decisions so failures can be
investigated months later rather than just detected. Each layer
addresses a specific failure mode; together they turn probabilistic
extraction into a reliable production system.

If you can recite that from memory, you have Domain 4's content.

---

## Where this fits in the whole study repo

| Scenario | Domain coverage | What it teaches |
|---|---|---|
| 1. Customer Support | D1 27% + D2 18% + D5 partial | Tools, hooks, structured errors |
| 2. Claude Code Dev Workflow | D3 partial | CLAUDE.md, skills, slash commands |
| 3. Multi-Agent Research | D1 ext + D2 ext + D5 ext | Coordinator, subagents, provenance |
| 4. Developer Productivity | D2 ext + D1 + D5 | Built-in tools, sessions, scratchpads |
| 5. CI/CD with Claude Code | D3 closes + D4 intro | Non-interactive flags, multi-pass, batch vs sync |
| 6. Structured Data Extraction | D4 deep + D5 ext | Schemas, validation-retry, confidence, provenance |

**Every domain. Every task statement. Every sample question.**

After completing this scenario, your study repo has hands-on grounding
for every concept the exam can test.

---

## License

Study material derived from the Claude Certified Architect — Foundations
exam guide. Patterns documented in Anthropic's public guidance.