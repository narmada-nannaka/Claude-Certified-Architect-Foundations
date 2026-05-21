# Scenario 3: Multi-Agent Research System

> A working implementation of a coordinator + specialist subagents
> research pipeline using the Claude Agent SDK pattern, covering Domain 1's
> multi-agent territory plus extensions to Domains 2 and 5 of the
> **Claude Certified Architect – Foundations** exam.

---

## What this scenario teaches

A coordinator agent that takes a research topic, delegates focused
sub-investigations to specialist subagents in parallel, aggregates
findings, and produces a structured report with full provenance —
plus an iterative refinement loop that detects coverage gaps and
self-corrects.

| Domain | Weight | Coverage in this scenario |
|---|---|---|
| **Domain 1** — Agentic Architecture & Orchestration | 27% (extends Scenario 1) | Multi-agent orchestration, Task tool, parallel emission, iterative refinement |
| **Domain 2** — Tool Design & MCP Integration | 18% (extends Scenario 1) | Scoped tool distribution across agents, scoped cross-role tools |
| **Domain 5** — Context Management & Reliability | 15% (extends Scenario 1) | Error propagation, information provenance through synthesis |

Three sample questions from the exam (Q7, Q8, Q9) map directly to
code in this folder.

---

## Sample questions answered by this folder

| Sample Q | Tests | Lives in |
|---|---|---|
| Q7 — coordinator decomposition failure | Where the bug is when subagents work but coverage is missing | `src/pipeline.py` (gap-fill feedback loop) |
| Q8 — error propagation from subagent | Structured error context vs generic "failed" | `src/subagents.py` + `src/coordinator.py` |
| Q9 — synthesis verification overhead | When to scope a tool vs route through coordinator | `src/synthesis.py` (verify_fact tool) |

---

## Architecture at a glance

```
                 ┌─────────────────────────────────┐
                 │  User: research topic           │
                 └────────────┬────────────────────┘
                              ▼
        ┌───────────────────────────────────────────────┐
        │  Pipeline orchestrator (src/pipeline.py)      │
        │  - Runs coordinator                           │
        │  - Runs synthesis                             │
        │  - Loops on coverage gaps (up to 3 rounds)    │
        └────────────┬──────────────────────────────────┘
                     ▼
        ┌───────────────────────────────────────────────┐
        │  Coordinator (src/coordinator.py)             │
        │  - Decomposes topic into subtopics            │
        │  - Emits parallel Task tool calls             │
        │  - Aggregates structured findings             │
        └────────────┬──────────────────────────────────┘
                     ▼ (Task tool dispatch)
        ┌─────────────────────┬─────────────────────────┐
        │  web_research       │  document_analysis      │
        │  subagent           │  subagent               │
        │  (search_web only)  │  (analyze_documents)    │
        └────────────┬────────┴───────────┬─────────────┘
                     │   structured       │
                     │   findings         │
                     ▼                    ▼
        ┌───────────────────────────────────────────────┐
        │  Aggregated findings list                     │
        └────────────┬──────────────────────────────────┘
                     ▼
        ┌───────────────────────────────────────────────┐
        │  Synthesis agent (src/synthesis.py)           │
        │  Tools:                                       │
        │   - verify_fact (scoped, simple lookups)      │
        │   - submit_synthesis_report (structured out)  │
        │  Output: report with domain sections,         │
        │  conflicts, coverage_gaps                     │
        └────────────┬──────────────────────────────────┘
                     ▼
        ┌───────────────────────────────────────────────┐
        │  If coverage_gaps non-empty:                  │
        │  pipeline dispatches gap-fill investigations  │
        │  and re-runs synthesis (up to MAX rounds)     │
        └────────────┬──────────────────────────────────┘
                     ▼
                Final structured report
```

Four collaborating components, each with a focused role.

---

## The Task tool: how subagents get spawned

The Task tool is mechanically just another tool the coordinator can
call. Its "implementation" runs the named subagent's agent loop and
returns the subagent's structured output as the tool result.

Key architectural points:

- **Only the coordinator has the Task tool.** Subagents can't spawn
  sub-subagents (which would create recursion and observability loss).
- **Subagents start with empty context.** They only see what the
  coordinator packs into the Task tool's `prompt` input. They do NOT
  inherit the coordinator's conversation history.
- **Parallel emission**: the coordinator can emit multiple Task tool
  calls in a single response. The loop dispatches them all together.
  Same mechanism as parallel tool calls in any agent — Task isn't
  architecturally special.

---

## Subagent specialization: scoped tools per role

Per Task 2.3, each subagent has narrow `allowed_tools`:

| Subagent | Allowed tools | Why scoped |
|---|---|---|
| web_research | `search_web` | News articles, industry reports, current events |
| document_analysis | `analyze_documents` | Papers, studies, in-depth reports |
| synthesis | `verify_fact`, `submit_synthesis_report` | Simple verification + structured output submission |

A synthesis agent without web_search can't accidentally "research more"
mid-synthesis — the specialization is structural, not just instructional.

---

## Prerequisites

- Python 3.10+
- An Anthropic API key
- PowerShell (Windows)
- VS Code recommended

No MCP server library required for this scenario — subagents are
dispatched in-process for clarity. The same architectural patterns
apply when using the real Agent SDK with MCP-served tools.

---

## Quick start

```powershell
cd scenario-03-multi-agent-research
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
# Edit .env, add: ANTHROPIC_API_KEY=sk-ant-...

# Verify tests pass (no API calls, runs in <2 seconds)
pytest -v

# Run the full pipeline against a real topic (uses API)
python scripts/run_research.py "the impact of AI on creative industries"

# See the failure-recovery + verify_fact demo
python scripts/demo_failure_recovery.py
```

---

## Project layout

```
scenario-03-multi-agent-research/
├── README.md
├── requirements.txt
├── pyproject.toml
├── .env.example
│
├── src/
│   ├── agent_loop.py          # Reusable loop with stop_reason control
│   ├── subagents.py           # AgentDefinition registry + dispatch
│   ├── coordinator.py         # Coordinator + Task tool dispatch
│   ├── synthesis.py           # Synthesis schema + verify_fact tool
│   ├── pipeline.py            # End-to-end pipeline with gap-fill loop
│   └── fake_data.py           # Mock findings across creative domains
│
├── tests/
│   ├── test_agent_loop.py
│   ├── test_subagent_dispatch.py
│   ├── test_coordinator_dispatch.py
│   ├── test_synthesis_structure.py
│   ├── test_provenance.py
│   ├── test_coverage_gaps.py
│   ├── test_error_propagation.py
│   └── test_verify_fact.py
│
└── scripts/
    ├── run_research.py            # Full pipeline runner
    └── demo_failure_recovery.py   # Demonstrates Q8 + Q9 patterns
```

---

## The six milestones

### M1 — Scaffold and fake research data
Project structure plus a deliberately multi-domain findings fixture
(visual arts, music, writing, film, theatre, etc.) so coordinator
decomposition failures are visible in test output.

### M2 — Specialist subagents with scoped tools
**Tests Task 1.3, 2.3.** Two AgentDefinitions: `web_research` and
`document_analysis`. Each has its own system prompt and scoped
`allowed_tools` — no cross-specialization. Each returns structured
`SubagentResult` objects with full provenance.

### M3 — Coordinator with Task tool
**Tests Task 1.3, 2.3. Foundation for Q7.** The coordinator's only
tool is `Task`. When the coordinator decomposes a topic and emits
multiple Task calls in one response, all subagents run in parallel.
The Task tool's implementation dispatches to the subagent registry.

### M4 — Synthesis with provenance preservation
**Tests Task 5.6, Task 4.3 preview.** Synthesis output is enforced via
a `tool_use` schema. Every claim carries `source_name` and
`publication_date_iso`. Conflicts preserve both sources. Coverage gaps
are surfaced as a required structured field.

### M5 — Coverage-gap feedback loop
**Tests Task 1.2. Maps to Sample Q7.** If synthesis surfaces gaps,
the pipeline dispatches targeted gap-fill investigations and re-runs
synthesis. Up to 3 refinement rounds (cap as safety net, not primary
control). The cap engages when gaps persist across rounds.

### M6 — Error propagation + verify_fact scoped tool
**Tests Task 5.3, 2.3. Maps to Sample Q8 and Q9.** Subagent failures
return structured error context (category, retryability, attempted
query, alternatives) — not generic "failed" strings. The synthesis
agent gets a bounded `verify_fact` tool for simple lookups (85% case),
while complex verifications structurally defer back to coordinator-
level investigation (15% case).

---

## Three exam-aligned demos

### Demo 1: Watch the coordinator decompose and delegate

```powershell
python scripts/run_research.py "the impact of AI on creative industries"
```

Watch the output for:
- Number of subagent invocations vs coordinator iterations
  (low iterations + many invocations = parallel emission working)
- Domains covered in the final report
- Gap history: did the initial decomposition need refinement?

If the coordinator narrowly decomposes (e.g., only visual arts), the
gap-fill loop catches the missing domains (music, writing, film) and
re-investigates — Sample Q7's failure mode handled architecturally.

### Demo 2: Failure recovery and verify_fact

```powershell
python scripts/demo_failure_recovery.py
```

Simulates a `web_research` timeout. Watch how:
- The subagent returns structured error context (not a generic failure)
- The coordinator can recover by delegating to `document_analysis`
- The pipeline produces a report from partial findings rather than
  failing entirely
- Synthesis may invoke `verify_fact` for simple date/name lookups

### Demo 3: Inspect what made it through

After running either demo, examine the gap history and invocation
list. Each gap-fill invocation is marked with `phase: gap_fill` and a
`gap_target` domain, so you can audit which gaps were filled by which
follow-up investigations.

---

## Studying with this code

### 1. Read the files in dispatch order

1. `src/fake_data.py` — see the fixture findings the system reasons against
2. `src/agent_loop.py` — the reusable loop reused by every agent
3. `src/subagents.py` — how AgentDefinitions and SubagentResults are shaped
4. `src/coordinator.py` — Task tool dispatch and ResearchSession aggregation
5. `src/synthesis.py` — the output schema and verify_fact scoped tool
6. `src/pipeline.py` — the gap-fill feedback loop tying it all together

Each file builds on the previous. By the time you read `pipeline.py`,
every primitive it uses is familiar.

### 2. Break things deliberately

- Comment out the parallel-emission instruction in
  `COORDINATOR_SYSTEM_PROMPT`. Watch iterations grow as the coordinator
  delegates serially.
- Set `MAX_REFINEMENT_ITERATIONS = 0` in `pipeline.py`. The initial
  decomposition's gaps go unfilled — Sample Q7's failure visible.
- Change `verify_fact`'s `"other"` claim_type to return a fake
  verification instead of "deferred." Synthesis fabricates verified
  facts that weren't actually checked.
- Remove `is_error` from `_simulate_failure_if_configured`'s return.
  The coordinator silently aggregates empty findings as if the search
  succeeded — Sample Q8's distractor C in action.

Each experiment maps to an exam distractor.

### 3. Re-read Sample Questions 7, 8, 9 with this code open

Each question's correct answer maps to a specific architectural pattern
in this folder. Use the scenario as a referenceable answer key.

---

## Common distractor patterns this code debunks

| Distractor | Why wrong | Reference |
|---|---|---|
| Blame downstream subagents when coverage is incomplete | The coordinator's decomposition is the bug | Sample Q7 / `pipeline.py` |
| Return generic "search unavailable" on subagent failure | Hides recovery context from coordinator | Sample Q8 / `_task_tool_implementation` |
| Mark subagent failure as empty-success | Silently corrupts research output | Sample Q8 / `test_error_propagation.py` |
| Terminate the whole workflow on one subagent failure | Throws away other subagents' work | Sample Q8 / pipeline degrades gracefully |
| Give synthesis agent full web search tools | Over-provisions; destroys specialization | Sample Q9 / scoped `verify_fact` |
| Batch synthesis's verification needs until end | Blocks synthesis progress; can't proceed | Sample Q9 / mid-synthesis tool invocation |
| Make verify_fact a PreToolUse hook on submit_synthesis_report | Verification is reasoning, not enforcement | Tool vs hook distinction |
| Skip publication_date_iso when source has no date | Loses temporal disambiguation | Task 5.6 / schema requires date |
| Resolve conflicts arbitrarily by picking one | Loses provenance and reader trust | Task 5.6 / schema's conflict structure |

---

## The Domain 1 multi-agent mental model in one paragraph

A coordinator decomposes a topic and dispatches Task tool calls — one
per investigation — to specialist subagents. Each subagent has its own
narrow tool set and starts with empty context, receiving only what the
coordinator packs in the Task tool's prompt input. Subagents run in
parallel when the coordinator emits multiple Task calls in one response.
Their outputs are aggregated into a findings list with full provenance
metadata (source, date, domain). A synthesis agent receives the findings
and produces a structured report via a schema-enforced tool call,
preserving claim-source mappings, annotating conflicts with both sides,
and surfacing coverage gaps as an explicit field. If gaps exist, the
pipeline dispatches targeted gap-fill investigations and re-runs
synthesis, up to a cap. Subagent failures return structured error
context — category, retryability, what was attempted, alternative
approaches — so the coordinator can make intelligent recovery decisions.
The synthesis agent has a scoped verify_fact tool for simple
verifications it can do without leaving its context; complex
verifications structurally defer back through the coordinator.

If you can recite that from memory, you have Scenario 3's architecture.

---

## Troubleshooting

### Tests fail with `ModuleNotFoundError: No module named 'src'`

Verify `pyproject.toml` includes:
```toml
[tool.pytest.ini_options]
pythonpath = ["."]
```
Run pytest from the scenario folder, not the repo root.

### Coordinator does everything serially (one subagent per iteration)

The model isn't reliably emitting parallel Task calls. Strengthen the
parallel-emission instruction in `COORDINATOR_SYSTEM_PROMPT`. If the
problem persists, add a few-shot example showing the desired pattern.

### Gap-fill loop runs full 3 iterations without filling gaps

The synthesis agent is reporting gaps for domains where the fake_data
fixture has no findings. Expected behavior when data isn't available.
Check `hit_iteration_cap == True` on the result; the report preserves
unfilled gaps so downstream callers know what couldn't be addressed.

### `verify_fact` is never invoked during synthesis

Verify_fact invocation is autonomous — the synthesis agent decides
when to use it based on the system prompt. If you want to see it fire
deterministically, modify the synthesis prompt to add: *"Before
finalizing your report, verify the date of any major event mentioned
using verify_fact."* The agent will then invoke it at least once.

### Real model produces nondeterministic output

Expected. Tests mock the API for determinism. The `scripts/run_research.py`
and demos use the real API, where run-to-run variability is normal.
The architectural invariants (structured output, provenance fields,
gap detection) hold regardless; the specific choices the model makes
about decomposition and emphasis vary.

---

## Where to go next

- **Scenario 4** (Developer Productivity) — extends this scenario's
  agent patterns into IDE-integrated workflows
- **Scenario 5** (CI/CD) — combines Domain 3's CI/CD piece with
  Domain 4 prompting patterns
- **Scenario 6** (Structured Extraction) — Domain 4 deep dive on
  JSON schemas, validation-retry loops, and the Message Batches API

---

## License

Study material derived from the Claude Certified Architect — Foundations
exam guide. Architectural patterns documented in Anthropic's public
guidance at https://code.claude.com/docs/en/best-practices.