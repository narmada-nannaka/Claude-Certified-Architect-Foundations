# Scenario 1: Customer Support Resolution Agent

> A working implementation of the customer-support scenario from the
> **Claude Certified Architect – Foundations** exam guide, built with the
> Claude Agent SDK, MCP tools, and structured hooks. Designed for hands-on
> exam preparation.

---

## What this scenario teaches

You're building an agent that handles real customer support cases — returns,
billing disputes, account questions — with a target of 80%+ first-contact
resolution while knowing when to escalate to a human.

The implementation exercises three exam domains:

| Domain | Weight | What you'll build for it |
|---|---|---|
| **Domain 1** — Agentic Architecture & Orchestration | 27% | Agent loop, hooks, multi-concern decomposition |
| **Domain 2** — Tool Design & MCP Integration | 18% | MCP server, tool descriptions, structured errors |
| **Domain 5** — Context Management & Reliability | 15% | Session state, escalation, error propagation |

Combined, these domains are **60% of the exam**, and four of the exam's
twelve sample questions map directly to code in this folder.

---

## Sample questions you'll be able to answer after building this

| Sample Q | What it tests | Where it lives in this code |
|---|---|---|
| Q1 — prerequisite enforcement | Hooks vs prompts for deterministic compliance | `src/hooks.py` (`pre_tool_use_hook`) |
| Q2 — tool selection reliability | Tool description quality | `src/mcp_server.py` (docstrings) |
| Q3 — escalation calibration | Explicit criteria with few-shot | `src/prompts.py` |
| Q8 — error propagation | Structured error context | `src/errors.py` |

---

## Architecture at a glance

┌─────────────────────────────────┐
             │  User (customer message)        │
             └────────────┬────────────────────┘
                          │
                          ▼
    ┌───────────────────────────────────────────────┐
    │  Agent Loop (src/agent.py)                    │
    │  • Sends to Claude API                        │
    │  • Inspects stop_reason ("tool_use"/"end_turn")│
    │  • Manages conversation history               │
    └────────────┬──────────────────────────────────┘
                 │
          tool_use blocks
                 │
                 ▼
    ┌───────────────────────────────────────────────┐
    │  PreToolUse Hook (src/hooks.py)               │
    │  • Identity verification prerequisite         │
    │  • Refund limit policy ($500)                 │
    │  • Returns (allow, replacement_result)        │
    └────────────┬──────────────────────────────────┘
                 │
          allow=True
                 │
                 ▼
    ┌───────────────────────────────────────────────┐
    │  MCP Tools (src/mcp_server.py)                │
    │  • get_customer (verify identity)             │
    │  • lookup_order (order details)               │
    │  • process_refund (issue refunds)             │
    │  • track_shipment (in-transit lookups)        │
    │  • escalate_to_human (structured handoff)     │
    └────────────┬──────────────────────────────────┘
                 │
            tool result
                 │
                 ▼
    ┌───────────────────────────────────────────────┐
    │  PostToolUse Hook (src/hooks.py)              │
    │  • Normalize epochs → ISO 8601                │
    │  • Translate numeric status codes             │
    │  • Trim verbose fields                        │
    │  • Preserve raw values under __raw_           │
    └────────────┬──────────────────────────────────┘
                 │
          tool_result block
                 │
                 ▼
          [back to Agent Loop]

Two hook layers + one MCP tool layer. Three single-responsibility components.

---

## Prerequisites

- **Python 3.10+** — verify with `python --version`
- **Anthropic API key** — get one at https://console.anthropic.com
- **PowerShell** (Windows) — instructions use Windows commands
- **VS Code** recommended — for stepping through the agent loop in a debugger

---

## Quick start

```powershell
# 1. From the scenario folder, create and activate a virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1
# If activation fails: Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure your API key
copy .env.example .env
# Then edit .env and add: ANTHROPIC_API_KEY=sk-ant-...

# 4. Verify with the test suite (no API calls, runs in <2 seconds)
pytest -v

# 5. Run the interactive demo (uses real API calls — counts against your quota)
python scripts/run_demo.py
```

If `pytest` finds and passes all tests, your environment is ready.

---

## The six milestones, mapped to exam task statements

This scenario was built in six milestones, each reinforcing specific task
statements from the exam guide.

### Milestone 1 — Project scaffold
Sets up the virtual environment, dependencies, and folder structure.
Not directly exam-tested, but establishes the test infrastructure that
makes every later milestone verifiable.

### Milestone 2 — MCP server with structured errors
**Tested**: Task 2.1 (tool descriptions), Task 2.2 (structured errors),
Task 2.3 (tool distribution).

Key files: `src/mcp_server.py`, `src/errors.py`, `tests/test_tools.py`.

**The lesson**: tool descriptions are the primary mechanism Claude uses
for tool selection. Minimal descriptions cause misrouting. Every tool
here has a description with purpose, inputs, example queries, edge cases,
and explicit "do NOT use this for X" negative guidance — the recipe
Sample Question 2's correct answer prescribes.

### Milestone 3 — Agent loop with `stop_reason` handling
**Tested**: Task 1.1 (agentic loops), Task 1.3 (parallel tool emission).

Key files: `src/agent.py`, `tests/test_agent_loop.py`.

**The lesson**: the model's `stop_reason` is the authoritative termination
signal. Anti-patterns the exam tests against: parsing natural language
for completion ("let me know if..."), using iteration caps as the
primary stop, treating text blocks as completion indicators. The loop
here checks `stop_reason` exclusively and falls back to a safety cap
only as a circuit breaker.

### Milestone 4 — PostToolUse hook for data normalization
**Tested**: Task 1.5 (hooks for normalization), Task 5.1 (trimming context).

Key files: `src/hooks.py` (post-hook section), `tests/test_hooks.py`.

**The lesson**: heterogeneous data formats (Unix epochs, ISO 8601,
numeric status codes) should be harmonized via hooks, not via prompt
instructions. The hook gives the model a consistent view of data
regardless of which backend the tool wraps.

### Milestone 5 — PreToolUse gate (the highest-yield milestone)
**Tested**: Task 1.4 (workflow enforcement), Task 1.5 (hooks for
compliance), Task 5.2 (escalation patterns).

Key files: `src/hooks.py` (pre-hook section), `tests/test_prerequisite_gate.py`.

**The lesson — this is Sample Question 1 directly.** When deterministic
compliance is required (e.g., verifying customer identity before
financial operations), prompt instructions have a non-zero failure
rate. The PreToolUse gate enforces:

1. Identity-verification prerequisite: `lookup_order`, `process_refund`,
   `track_shipment` all blocked until `get_customer` succeeds.
2. Refund limit: $500 cap enforced regardless of prompt instructions.

Try the demo prompt:
> *"Please refund order O-5001 for $50 — the widget was scratched."*

You'll watch the agent attempt `process_refund` first (the 12% pattern
from Sample Q1), get blocked by the gate, read the structured error,
call `get_customer` to satisfy the prerequisite, then retry the refund
successfully. This is *deterministic recovery from a structured error*
— the exam's gold-standard pattern.

### Milestone 6 — Multi-concern decomposition + structured escalation
**Tested**: Task 1.4 (multi-step workflows), Task 1.6 (decomposition),
Task 5.2 (escalation calibration).

Key files: `src/prompts.py`, `src/mcp_server.py` (escalate_to_human),
`tests/test_escalation.py`.

**The lesson**: real customer messages contain multiple distinct
concerns. The agent should decompose them, investigate in parallel
(using the parallel-tool-call mechanism from M3), and synthesize a
unified response. The escalation handoff must be self-contained —
the human reviewer has no access to the conversation transcript.

---

## Three demo flows to walk through

These are the demos the exam patterns are designed around. Run each
one and watch the transcript carefully.

### Demo 1: The prerequisite gate fires and recovery happens

You: Please refund order O-5001 for $50, the widget was scratched.
Expected Trace: 

→ process_refund(...) [BLOCKED business]
⚠ gate violations this turn: 1

**What this proves**: prompt instructions said to verify first, but the
model didn't (the 12% from Sample Q1). The gate caught it. The agent
read the structured error, understood the recovery path, and completed
the workflow.

### Demo 2: Refund limit triggers escalation

You: I'm C-1002. Refund order O-5003 for the full amount of $1299.
Expected trace: 

→ get_customer(...) [ok]
→ lookup_order(...) [ok]
→ process_refund(...) [BLOCKED business]
→ escalate_to_human(...) [ok]

**What this proves**: policy lives in one place (the hook). Changing
the limit is a one-line edit. The agent didn't need to remember the
$500 number; the error message told it to escalate, and it complied.

### Demo 3: Multi-concern parallel investigation

You: Hi I'm test1003@example.com. Three things:

order O-5004 came in the wrong color, I want a refund
O-5005 was supposed to arrive last week, where is it
there's a charge for O-5006 I don't remember

Expected trace (with some variability):

→ get_customer(...) [ok]
→ lookup_order(O-5004) [ok]     ← three calls in
→ lookup_order(O-5005) [ok]     ← one response =
→ lookup_order(O-5006) [ok]     ← parallel emission
→ process_refund(O-5004, ...) [ok]
→ track_shipment(O-5005) [ok]

**What this proves**: the loop handles multiple `tool_use` blocks in a
single response (Task 1.3's parallel-tool-call mechanism). One round
trip instead of three. This is the same primitive that powers parallel
subagent spawning in Scenario 3.

---

## Studying with this code

Three suggestions for getting the most exam value out of this scenario.

### 1. Run the demos before reading the code

Watch the agent's behavior first, then dive into the source to
understand *why* it behaved that way. This is the opposite of how
most documentation flows, but it's how the exam tests: it gives you
a behavior pattern and asks you to identify the architectural cause.

### 2. Break things deliberately

Each component is small and well-tested. Try these:

- Comment out the `post_tool_use_hook` line in `agent.py`. Re-run
  Demo 1. Watch the agent reason about Unix epochs and sometimes
  surface them to the user.
- Comment out the `pre_tool_use_hook` call. Re-run Demo 1 a few
  times. You'll see the 12% misrouting failure mode in action.
- Weaken a tool description in `mcp_server.py` to just `"Look up
  a customer"`. Run `python scripts/test_tool_routing.py`. Watch
  routing reliability collapse.

Each of these maps to an exam distractor option. Feeling the failure
mode is the difference between knowing the right answer and
*recognizing* the right answer under time pressure.

### 3. Re-read Sample Questions 1–3 and 8 with this code open

The exam guide's sample questions become much more concrete when
you can point to specific lines that implement the correct answer.
Use this scenario as a referenceable answer key for those four.

---

## Common exam-distractor patterns this code lets you debunk

| Distractor pattern | Why it's wrong | Where to look in this code |
|---|---|---|
| "Strengthen the system prompt for X" | Probabilistic compliance, won't eliminate failure mode | `src/hooks.py` shows the deterministic alternative |
| "Add few-shot examples" | Same — reduces but doesn't eliminate | Same |
| "Use a higher-tier model" | Same instruction-following architecture, just better | Same |
| "Implement a routing classifier upfront" | Addresses tool *availability* when the problem is tool *ordering* | `pre_tool_use_hook` enforces ordering directly |
| "Self-reported confidence scores for escalation" | LLM confidence is poorly calibrated | `src/prompts.py` uses explicit criteria instead |
| "Sentiment-based escalation" | Sentiment doesn't correlate with case complexity | Same |
| "Return a generic 'failed' error" | Hides recovery context from the agent | `src/errors.py` taxonomy |

---

## License & attribution

This is study material derived from the Claude Certified Architect –
Foundations exam guide. Code is for educational use; the patterns
implemented here are documented in Anthropic's public guidance at
https://code.claude.com/docs/en/best-practices.

The fake customer data uses RFC 2606 reserved domains (`example.com`)
to make it unambiguous that no real accounts are referenced.