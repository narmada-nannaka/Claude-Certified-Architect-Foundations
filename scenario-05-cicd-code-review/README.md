# Scenario 5: Claude Code for Continuous Integration

> A working CI pipeline that runs Claude Code non-interactively against
> pull requests, producing calibrated, structured findings — covering
> Task 3.6 (the final Domain 3 task) plus the introduction to Domain 4
> of the **Claude Certified Architect – Foundations** exam.

---

## What this scenario teaches

How Claude Code participates as a deterministic pipeline component in
CI/CD workflows: non-interactive invocation, structured JSON output,
explicit review criteria, few-shot calibration, multi-pass architecture
for large PRs, and the synchronous vs Message Batches API decision.

| Domain | Weight | Coverage in this scenario |
|---|---|---|
| **Domain 3** — Claude Code Configuration & Workflows | 20% (Task 3.6 closes) | Non-interactive CLI flags, structured CI output |
| **Domain 4** — Prompt Engineering & Structured Output | 20% (intro) | Explicit criteria, few-shot examples, batch vs sync, multi-pass |

Sample questions mapped to this scenario:

| Sample Q | What it tests | Reference |
|---|---|---|
| Q10 — non-interactive mode | `-p` flag vs invented alternatives | Concept 1 |
| Q11 — batch vs synchronous | Match API to whether something waits on the result | Concept 7 |
| Q12 — multi-pass for large PRs | Per-file + integration pass, not single-pass | Concept 3 |

---

## The three sentences to memorize

These encapsulate Scenario 5's exam content. If you can recite them cold
you have the scenario.

> **1. Non-interactive CI uses `-p` plus `--output-format json` plus
> `--json-schema`. These flags turn Claude Code into a deterministic
> pipeline component that produces machine-parseable structured output.**

> **2. API selection follows blocking: synchronous when something waits
> on the result (pre-merge checks, pre-deploy scans), Message Batches
> when nothing does (overnight reports, weekly audits). Batch trades
> 50% cost savings for up to 24-hour completion times.**

> **3. Large PRs need multi-pass architecture: per-file passes for
> local issues plus a separate integration pass for cross-file concerns.
> Single-pass review of 10+ files suffers attention dilution and
> produces inconsistent, sometimes contradictory findings.**

---

## Architecture at a glance

```
              ┌──────────────────────────────────┐
              │  PR opened / synchronized        │
              └────────────┬─────────────────────┘
                           ▼
      ┌────────────────────────────────────────────────┐
      │  CI workflow (GitHub Actions / equivalent)     │
      │  - Checkout PR with full history               │
      │  - Install Claude Code                         │
      │  - Run pipeline script with base SHA           │
      └────────────┬───────────────────────────────────┘
                   ▼
      ┌────────────────────────────────────────────────┐
      │  pipeline.py (CI runner simulator)             │
      │  - Loads prompt from prompts/review_prompt.txt │
      │  - Loads schema from review_schema.json        │
      │  - Loads project context from CLAUDE.md        │
      │  - Invokes: claude -p --output-format json     │
      └────────────┬───────────────────────────────────┘
                   ▼
      ┌────────────────────────────────────────────────┐
      │  Mode selection:                               │
      │   1. Single-pass review (small PRs)            │
      │   2. Multi-pass: per-file + integration (large)│
      │   3. Independent reviews compared (high stakes)│
      │   4. Format findings by confidence for PR      │
      └────────────┬───────────────────────────────────┘
                   ▼
      ┌────────────────────────────────────────────────┐
      │  Output: structured JSON findings              │
      │   - severity (critical/warning/info)           │
      │   - category (bug/security)                    │
      │   - confidence (high/medium/low)               │
      │   - file:line location                         │
      │   - suggested_fix                              │
      │   - reasoning                                  │
      └────────────┬───────────────────────────────────┘
                   ▼
      ┌────────────────────────────────────────────────┐
      │  Routing by confidence:                        │
      │   - High → blocking PR comments                │
      │   - Medium → review required                   │
      │   - Low → informational                        │
      └────────────────────────────────────────────────┘
```

Five exam-tested concepts, one workflow.

---

## The iterative refinement journey

This scenario teaches **how prompts are actually built in production**:
not in one shot, but through observing failure modes and adjusting.

| Iteration | Prompt characteristic | Output quality |
|---|---|---|
| 1 (starter) | Vague: "be thorough, check everything" | Noisy — bugs mixed with style and naming opinions |
| 2 (explicit criteria) | Categorical: "report ONLY bugs and security; do NOT report style" | Cleaner — false positives drop significantly |
| 3 (few-shot) | Adds 3 examples covering ambiguous cases | Consistent format + better judgment on edge cases |
| 4 (multi-pass) | Per-file passes + integration pass | Catches cross-file bugs that single-pass missed |
| 5 (independent review) | Two runs compared, confidence calibrated | Calibrated reliability for routing |

This progression IS the exam content for Task 3.5 (iterative
refinement). Each iteration is a testable improvement against the
previous one.

---

## Prerequisites

- Claude Code installed (`npm install -g @anthropic-ai/claude-code`)
- Python 3.10+
- An Anthropic API key
- PowerShell (Windows) or bash (macOS/Linux)
- VS Code recommended

---

## Quick start

```powershell
cd scenario-05-cicd-code-review

# Python environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# API key
copy .env.example .env
# Edit .env: ANTHROPIC_API_KEY=sk-ant-...

# Run the pipeline
python pipeline.py
```

You'll see a menu. Type `1` to run a single-pass review with the
starter prompt against the PR files. Reviews are saved to `output/`
with timestamps for comparison across iterations.

---

## Project layout

```
scenario-05-cicd-code-review/
├── README.md
├── CLAUDE.md                       # Project context for CI invocations
├── pipeline.py                     # CI runner simulator
├── manage.py                       # restart/solve commands
├── review_schema.json              # JSON schema for findings
├── requirements.txt
├── .env.example
│
├── prompts/
│   ├── review_prompt.txt           # Iteratively refined (vague → explicit → few-shot)
│   └── integration_prompt.txt      # Cross-file integration pass prompt
│
├── pr_files/                       # Simulated pull request
│   ├── auth.py                     # Has check_permission()
│   ├── orders.py                   # Cross-file bug: doesn't call check_permission()
│   ├── utils.py                    # parse_json_safe (ambiguous case)
│   └── test_utils.py               # Existing tests (CLAUDE.md references these)
│
├── output/                         # Timestamped review outputs (created at runtime)
│
└── .github/workflows/
    └── claude-review.yml           # GitHub Actions CI configuration
```

---

## The seven concepts in detail

### Concept 1: Non-interactive CI invocation (Task 3.6, Sample Q10)

The pipeline invokes Claude Code with three exam-tested flags:

```python
subprocess.run(
    ["claude", "-p", prompt, "--output-format", "json"],
    capture_output=True, text=True, timeout=300,
)
```

| Flag | Purpose |
|---|---|
| `-p` (`--print`) | Non-interactive mode — required for CI |
| `--output-format json` | Wraps response in a JSON envelope |
| `--json-schema` (where supported) | Validates output against schema |

Without `-p`, Claude Code waits for terminal input and the pipeline hangs.

### Concept 2: Iterative prompt refinement (Task 3.5, Task 4.1)

The lab walks you through three iterations of `review_prompt.txt`:

- **Vague** → noisy output mixing bugs with style opinions
- **Explicit categories** ("report ONLY bugs and security; do NOT
  report style") → false positives drop
- **Few-shot examples** → consistent format + better judgment on
  ambiguous cases like `parse_json_safe` returning None

Each iteration is measurable: save outputs to `output/` and compare
before/after.

### Concept 3: Multi-pass review for large PRs (Task 4.6, Sample Q12)

`pipeline.py`'s `run_multi_pass()` makes N+1 invocations:

```
Pass 1: claude -p (auth.py only) → local findings
Pass 2: claude -p (orders.py only) → local findings
Pass 3: claude -p (utils.py only) → local findings
Pass 4: claude -p (all files + per-file findings) → cross-file findings
```

The cross-file pass catches the deliberate bug where `orders.py` doesn't
call `check_permission()` from `auth.py` — something single-pass review
typically misses due to attention dilution.

### Concept 4: Independent review + confidence calibration (Task 4.6)

`run_independent_review()` runs two complete reviews on the same diff
and compares findings:

- Findings BOTH catch → high reliability
- Findings only ONE catches → medium reliability
- Routing by `confidence` field:
  - High → blocking PR comments
  - Medium → review required
  - Low → informational

This is calibrated routing, NOT consensus filtering (which would
suppress real bugs).

### Concept 5: CLAUDE.md as CI context (Task 3.6)

The same `CLAUDE.md` that guides interactive development also provides
context to `claude -p` invocations. When the pipeline runs from the lab
folder, Claude Code automatically loads this file. The "Existing test
coverage" section is a good example: it lists what tests already exist
so test-generation invocations don't produce duplicates.

```markdown
### Existing test coverage

The following test files already exist. When generating new tests, do
NOT suggest tests for scenarios already covered:

- pr_files/test_utils.py covers:
  - validate_email: valid format, missing @, missing domain, empty
  - format_currency: positive amount, zero, None
  - truncate_string: short, long, empty, exact length
```

### Concept 6: Direct execution (`-p`) vs Plan mode (Task 3.4)

The pipeline uses `claude -p` everywhere (direct execution; no human
in the loop). Contrast with **plan mode** (`Shift+Tab` or `/plan` in
interactive Claude Code), which proposes a plan and waits for approval.

- **`-p`**: CI pipelines, automated reviews, test generation
- **Plan mode**: complex investigation, multi-file refactoring,
  architectural decisions
- **Combine**: CI flags issues with `-p`; developer investigates
  interactively with plan mode

### Concept 7: Synchronous vs Message Batches API (Task 4.5, Sample Q11)

This pipeline uses synchronous invocations because pre-merge checks
block the developer. For non-blocking workloads, the Message Batches API
offers 50% cost savings at the price of up to 24-hour processing time.

| Workflow | API | Why |
|---|---|---|
| Pre-merge PR review | Synchronous | Developer blocked |
| Pre-deploy security scan | Synchronous | Deploy blocked |
| Weekly tech debt report | Message Batches | Nobody waiting; 50% cost savings |
| Nightly test generation | Message Batches | Latency tolerant |
| Monthly architectural audit | Message Batches | Long analysis, no SLA |

Match the API to whether something is waiting on the result.

---

## Studying with this code

### 1. Run the iterative refinement journey

Start with the vague starter prompt and run option 1. Save the output.
Then replace the prompt with the explicit-criteria version (per Step 4
in the lab guide) and run again. Compare counts and quality of
findings. Then add the few-shot examples (Step 5) and run a third time.

You should see false positives drop measurably with each iteration.
This direct observation IS the exam content for Task 3.5.

### 2. Compare single-pass and multi-pass on the same PR

Run option 1 (single-pass) against the same PR files. Note whether it
catches the cross-file bug (orders.py missing the auth check).

Then run option 2 (multi-pass). The integration pass should surface
the cross-file bug that single-pass missed. This concrete demonstration
of Sample Q12's architectural pattern.

### 3. Run two independent reviews and look at the overlap

Run option 3 (independent review comparison). Note which findings both
reviews agree on (high reliability) and which only one catches
(broader coverage but lower individual reliability).

### 4. Format findings by confidence

Run option 4 after any review. Findings get sorted into:
- BLOCKING (high confidence)
- REVIEW REQUIRED (medium confidence)
- INFORMATIONAL (low confidence)

This demonstrates calibrated routing — the production pattern for
turning Claude's findings into actionable PR comments.

---

## Common distractor patterns this code debunks

| Distractor | Why wrong | Reference |
|---|---|---|
| `CLAUDE_HEADLESS=true` env var for non-interactive | Invented feature with plausible name | Sample Q10 |
| `< /dev/null` to fix Claude Code hanging | Workaround that doesn't address interactive-mode state | Sample Q10 |
| `--batch` flag for non-interactive Claude Code | Batches API isn't a CLI flag | Sample Q10 |
| Batch processing with polling for pre-merge | Batch has no SLA; polling doesn't bound latency | Sample Q11 |
| Batch results have ordering issues | Misconception — `custom_id` correlates explicitly | Sample Q11 |
| Hybrid batch + sync fallback for everything | Adds complexity without addressing the underlying mismatch | Sample Q11 |
| Require developers to split large PRs | Shifts system problem to developer burden | Sample Q12 |
| Use a higher-tier model with larger context | Confuses capacity with attention quality | Sample Q12 |
| Three-pass consensus (only flag if 2/3 agree) | Suppresses real bugs at the cost of completeness | Sample Q12 |
| Vague "be thorough" instructions | Vague instructions produce vague output | Task 4.1 |
| Skip few-shot examples — instructions alone suffice | Few-shot is the most effective technique for consistency | Task 4.2 |
| Single-pass for any PR size | Attention dilution above ~5 files | Task 4.6 |

---

## The Domain 4 prompting mental model in one paragraph

When Claude Code reviews code in a CI pipeline, the prompt is a contract
that gets earned through iteration. Vague instructions like "be thorough"
produce noisy output; replacing them with explicit categorical criteria
(report ONLY bugs and security, do NOT report style) eliminates the
noise. Few-shot examples covering ambiguous cases (acceptable patterns,
edge-case judgments) make formatting consistent and improve judgment on
patterns not literally in the examples. For large PRs, single-pass
review suffers attention dilution — fix it with per-file passes that
have bounded scope plus an integration pass focused on cross-file
concerns. Independent runs broaden coverage; per-finding confidence
calibration enables routing the results (high confidence blocking,
low confidence informational) rather than suppressing them through
consensus filtering. CLAUDE.md provides project context to both
interactive developers and CI runs from the same file. The synchronous
API is right when something is waiting on the result; the Message
Batches API is right when nothing is — 50% cost savings, up to 24-hour
window.

If you can recite that from memory, you have Scenario 5's content.

---

## Lessons learned (infrastructure side)

Building this lab on Windows surfaced several real cross-platform
scripting issues that aren't exam content but are worth knowing:

- **PowerShell external command output is a string array**, not a
  string. Use `-join "`n"` before string operations.
- **PowerShell 5.1 writes UTF-8 BOM by default**. Use
  `[System.IO.File]::WriteAllText` with `UTF8Encoding($false)` for
  cross-platform-compatible files.
- **PowerShell argument passing to external programs is fragile** for
  multi-line strings. Use a temp file: write the prompt to a temp file
  with `Get-Content -Raw`, then pass to the external command.
- **Use Python for orchestration** when Python is available — its
  `subprocess` handling is more reliable than PowerShell's external-
  command invocation for complex prompts.

These are general scripting hygiene lessons, not certification content.

---

## Troubleshooting

### Pipeline says "no changes to review"

The runner's diff detection compares `BaseSha..HEAD` first; if that's
empty, it falls back to working-tree diff against `BaseSha`. For local
testing, make sure you have either committed changes against a base
commit OR uncommitted working-tree changes against `HEAD`.

### Claude Code hangs at "Invoking Claude Code review..."

If `claude -p "test"` works directly in your terminal, the issue is in
how the pipeline invokes it. Common causes (all addressed in the Python
pipeline implementation):
- Multi-line prompt not properly escaped → write to temp file first
- API key not in current shell session → check `$env:ANTHROPIC_API_KEY`
- Prompt too large → check prompt length before invoking

### Schema file not found

Run from the scenario folder, not from the repo root. The pipeline
resolves paths relative to its own location.

### Sample diff doesn't apply

`git apply --no-index` requires the patch's expected "before" content
to match exactly. If you've modified files between generating and
applying, regenerate. For local testing, you can modify files directly
in your editor instead of applying patches.

### No blocker findings reported when SQL injection is in the diff

This is a calibration outcome, not a bug. Either:
- The diff Claude saw was empty (working-tree vs HEAD mismatch — check
  with `git diff HEAD` first)
- The prompt's blocker criteria need strengthening with a specific
  SQL-injection few-shot example
- The diff is large enough that attention is diluted — try multi-pass

---

## Where to go next

- **Scenario 6** (Structured Data Extraction) — Domain 4 deep dive:
  JSON schemas for extraction tasks, validation-retry loops with error
  feedback to the model, batch API mechanics (custom_id correlation,
  failure resubmission), and confidence calibration for human review
  routing.

---

## License

Study material derived from the Claude Certified Architect — Foundations
exam guide. Patterns documented in Anthropic's public guidance.