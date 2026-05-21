# Scenario 4: Developer Productivity with Claude

> Calibration drills and patterns for using Claude Code effectively on
> a realistic codebase, covering Task 2.5 (built-in tools), Task 1.7
> (session management), and Task 5.4 (scratchpad persistence) of the
> **Claude Certified Architect – Foundations** exam.

---

## What this scenario teaches

How an agent uses built-in tools (Read, Write, Edit, Bash, Grep, Glob),
manages session state across investigations, and persists information
across forked contexts when working with developers on unfamiliar code.

| Domain | Weight | Coverage in this scenario |
|---|---|---|
| **Domain 2** — Tool Design & MCP Integration | 18% (Task 2.5 focus) | Built-in tool selection drills |
| **Domain 1** — Agentic Architecture & Orchestration | 27% (Task 1.7 focus) | Session resumption and fork_session |
| **Domain 5** — Context Management & Reliability | 15% (Task 5.4 focus) | Scratchpad persistence pattern |

This scenario doesn't map directly to a specific Sample Question, but
it sharpens distractor analysis for tool-selection and session-management
questions that appear across multiple other scenarios.

---

## Key concepts reinforced

| Concept | Reference |
|---|---|
| Incremental narrowing for codebase exploration | M1 drill E, M2 skill |
| When Edit fails vs when Read+Write is the right fallback | M1 drill C |
| Glob for file paths vs Grep for file content | M1 drills A, B, F |
| Bash only for execution, not file operations | M1 drill D |
| --resume for continuing valid prior context | M3 drill Q1 |
| fork_session for divergent branches from a shared baseline | M3 drill Q2 |
| Fresh session with summary when prior context is stale | M3 drill Q3 |
| Scratchpad files to survive fork boundaries | M2 skill |

---

## Architecture at a glance

```
   Developer task: "explore this codebase / refactor X / debug Y"
                              │
                              ▼
        ┌───────────────────────────────────────────────┐
        │  Tool selection (Task 2.5)                    │
        │   - Glob:  find files by name pattern         │
        │   - Grep:  find content in files              │
        │   - Read:  load file contents                 │
        │   - Edit:  modify unique text fragments       │
        │   - Write: replace entire file                │
        │   - Bash:  execute commands (tests, git, etc) │
        └────────────┬──────────────────────────────────┘
                     ▼
        ┌───────────────────────────────────────────────┐
        │  Skill: explore-codebase (with context: fork) │
        │   - Uses Read/Grep/Glob for breadth-first map │
        │   - Writes scratchpad to .claude/scratch/     │
        │   - Returns short summary to main session     │
        └────────────┬──────────────────────────────────┘
                     ▼
        ┌───────────────────────────────────────────────┐
        │  Session management (Task 1.7)                │
        │   - --resume <name>: continue prior context   │
        │   - fork_session:    branch from baseline     │
        │   - fresh + summary: when prior is stale      │
        └───────────────────────────────────────────────┘
```

Three exam-tested mechanisms applied to one realistic context.

---

## Tool selection decision flowchart

```
       "What do you want to do with files?"
                       │
   ┌──────────────┬────┴───────┬─────────────┐
   ▼              ▼            ▼             ▼
 Find files   Find content  Read full     Modify
 by name      in files      file content  file content
   │              │            │             │
   ▼              ▼            ▼             ▼
  Glob          Grep          Read         Edit (preferred)
                                           Read+Write (fallback)
                                           Bash (for execution)
```

Two qualifying questions:

- **Need to execute something (tests, git, scripts)?** → Bash
- **Will Edit's unique-match constraint fail?** → Read+Write

---

## Session management decision rules

| Situation | Right choice |
|---|---|
| Continuing same investigation; prior context still valid | `--resume <name>` |
| Branching into divergent approaches from shared analysis | `fork_session` |
| Picking up after files changed significantly | Fresh session + structured summary |
| Quick exploratory task; no need to preserve | Fresh session |

The decision criterion: **is prior context still valid AND useful for the next step?**

---

## Prerequisites

- Claude Code installed
- A real codebase to work against (this scenario provides a mock TS one)
- PowerShell (Windows)
- VS Code recommended

No Python venv needed — no agent code is written.

---

## Quick start

```powershell
cd scenario-04-developer-productivity

# View the mock project structure
tree /F

# Start Claude Code
claude

# Try the tool-selection drills (see Milestone 1 in this README)
# Try invoking the explore-codebase skill (Milestone 2)
# Walk through session management decisions (Milestone 3)
```

---

## Project layout

```
scenario-04-developer-productivity/
├── README.md
│
├── .claude/
│   ├── CLAUDE.md                      # tool-selection conventions
│   ├── scratch/                       # written by explore-codebase
│   └── skills/
│       └── explore-codebase/
│           └── SKILL.md               # with scratchpad persistence
│
└── src/                               # mock TypeScript codebase
    ├── index.ts
    ├── handlers/
    │   ├── order-handler.ts
    │   ├── user-handler.ts
    │   └── billing-handler.ts
    ├── repositories/
    │   ├── OrderRepository.ts
    │   └── UserRepository.ts
    └── utils/
        ├── logger.ts
        └── dates.ts
└── tests/
    └── order-handler.test.ts
```

---

## The three milestones

### M1 — Built-in tool selection drill
**Tests Task 2.5.** Six concrete tool-selection tasks against the mock
codebase, each with a correct tool combination and explicit wrong-answer
analysis:

- Find every place importing `OrderRepository` → **Grep**
- Find all test files → **Glob**
- Rename `cancelOrder` to `voidOrder` everywhere → **Grep + Edit** (Read+Write fallback)
- Run the test suite → **Bash**
- Trace `handleOrder`'s callers transitively → **incremental Grep + Read**
- Add `console.log` after every `logger.info` → **Grep + Edit per file**

Plus a CLAUDE.md tool-selection convention block for the team.

### M2 — Codebase-exploration skill with scratchpad persistence
**Tests Task 2.5 + Task 5.4.** Extends the Scenario 2 `explore-codebase`
skill by adding scratchpad persistence:

- The fork still isolates verbose exploration from the main session
- Detailed findings are written to `.claude/scratch/explore-<timestamp>.md`
- Follow-up questions can reference the scratchpad without re-exploring
- `allowed-tools` adds Write (constrained to scratch directory by convention)

This is the "make forked work survive" pattern from Task 5.4.

### M3 — Session resumption and fork_session
**Tests Task 1.7.** Conceptual drill (no code) on three session-management
patterns:

- **`--resume <name>`**: continue a named session when prior context still valid
- **`fork_session`**: branch from a shared analysis baseline to explore divergent approaches
- **Fresh session + summary injection**: when prior tool results are stale

Three scenarios that contrast the three choices, with worked decision-criteria.

---

## Three drill prompts to run in Claude Code

### Drill 1: Tool selection awareness

```
I need to add a deprecation warning to every call site of the
`legacy-utils` module. Walk me through how you would do this,
naming the specific tools you'd use in order.
```

You should see Claude reach for **Grep** first (find imports/usages),
then **Edit** per call site (insert the warning). If Claude proposes
reading all files or using Bash, the tool-selection conventions in
CLAUDE.md need strengthening.

### Drill 2: Skill invocation with scratchpad verification

```
Explore this codebase and give me an overview of the main areas.
```

After the skill runs, check that `.claude/scratch/` contains a new
exploration file. Open it — it should have the detailed findings
that didn't make it into the summary.

Then ask a follow-up that requires detail:

```
Which functions are defined in the order handler?
```

If the skill's scratchpad is structured well, Claude can answer from
it without re-running the exploration.

### Drill 3: Session-management calibration

Walk through these scenarios out loud (or in conversation with Claude
Code) and articulate the right choice for each:

- *"I'm continuing my debugging from this morning."* → `--resume`
- *"I want to evaluate Redis vs in-memory caching after our analysis."* → `fork_session`
- *"The auth code changed significantly since I last explored it."* → fresh + summary

The drill is calibration — when you see the right choice instinctively,
you're exam-ready on Task 1.7.

---

## Studying with this code

### 1. Run the M1 drills against a real codebase

The mock codebase is small enough that the drills are quick but realistic
enough that the tool selections have correct answers. After running
the six drills, you'll have built calibration that transfers to any
codebase.

### 2. Read the skill's SKILL.md carefully

The frontmatter changes from Scenario 2 (added Write to allowed-tools)
illustrate the trade-off between strict tool restriction and durable
persistence. The scratchpad-path-in-summary pattern is a small but
exam-tested detail.

### 3. Practice the session-management decision out loud

Sessions are the easiest exam topic to forget because there's no
visible artifact to point to. Articulating "resume vs fork vs fresh"
for each scenario you encounter cements the decision tree.

---

## Common distractor patterns this scenario debunks

| Distractor | Why wrong | Reference |
|---|---|---|
| Use Bash sed for cross-file substitutions | Cross-platform sed flag differences; not Claude-native | M1 / Drill 2 |
| Read all files to find a function | Wastes context; Grep does it incrementally | M1 / Drill 5 |
| Use Glob to search file contents | Glob matches names, not contents | M1 / Drill 1 |
| Edit when text appears multiple times in a file | Edit needs a unique match; use Read+Write | M1 / Drill 3 |
| Skill output replaces the need for persistence | Forks discard intermediate work; scratchpad survives | M2 |
| `--resume` when prior tool results are stale | Stale context produces wrong reasoning | M3 / Q3 |
| `fork_session` for continuing one investigation | Forks are for parallel branches, not continuations | M3 / Q1 |
| `--resume` for evaluating divergent approaches | Sequential resumes aren't independent branches | M3 / Q2 |

---

## The Scenario 4 mental model in one paragraph

When Claude Code works on a codebase, tool selection follows a clear
hierarchy: Glob finds files by path pattern, Grep finds content in
files, Read loads file contents, Edit modifies a unique text fragment,
Read+Write is Edit's fallback when uniqueness fails, and Bash exists
for genuine execution (running tests, git operations). Codebase
exploration follows the incremental narrowing pattern — start with
Grep on a target symbol, Read its file, Grep the broader surface,
repeat until you have orientation. When using skills with `context:
fork` to isolate verbose work, persist detailed findings to scratchpad
files in `.claude/scratch/` so follow-up questions can reference them
without re-exploring. For session continuity, use `--resume` when
prior context is still valid, `fork_session` when you want to explore
divergent approaches from a shared analysis baseline, and a fresh
session with structured summary injection when prior tool results
have become stale.

If you can recite that from memory, you have Scenario 4's content.

---

## Troubleshooting

### Claude defaults to Bash for file operations

Check `.claude/CLAUDE.md` includes the tool-selection conventions
section. If Claude is reaching for Bash when Glob/Grep/Edit would
suffice, the convention needs explicit emphasis. Add a line like
"Prefer Claude-native tools (Glob, Grep, Read, Edit) over Bash for
file operations. Use Bash only for execution: running tests, git
commands, build scripts."

### The explore-codebase skill doesn't write a scratchpad

Check:
1. `Write` is in the skill's `allowed-tools` frontmatter
2. The `.claude/scratch/` directory exists (Claude may not create it
   if missing). Run `mkdir .claude\scratch` to create it.
3. The skill's body has explicit instructions to write before
   returning the summary.

### Follow-up questions cause re-exploration despite scratchpad

The scratchpad's structure may be too sparse to answer specific
questions. Strengthen the skill's "Scratchpad persistence" section
to require a detailed "Symbol map" listing every public function/class
with its location. The scratchpad pays off when it's detailed enough
to answer typical follow-ups without re-exploration.

### --resume reports session not found

Sessions are named at start-time. If you ran `claude` without `--resume`
or didn't name the session, it wasn't saved under that name. Start
named sessions explicitly: some Claude Code versions use `--session
<name>` for naming; check `claude --help` for current syntax.

---

## Where to go next

- **Scenario 5** (CI/CD with Claude Code) — extends Domain 3 with
  Task 3.6 (non-interactive mode, --output-format json) plus Domain 4
  prompting patterns for code review
- **Scenario 6** (Structured Data Extraction) — full Domain 4 deep
  dive on JSON schemas, validation-retry loops, and the Message
  Batches API

---

## License

Study material derived from the Claude Certified Architect — Foundations
exam guide. Patterns documented in Anthropic's public guidance at
https://code.claude.com/docs/en/best-practices.