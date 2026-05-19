# Scenario 2: Claude Code for Team Development Workflows

> Configuration of Claude Code for a multi-area TypeScript/React project,
> covering Domain 3 of the **Claude Certified Architect – Foundations**
> exam. This scenario is configuration-heavy rather than code-heavy.

---

## What this scenario teaches

Configuring Claude Code so a team gets consistent assistance across:

- Different coding conventions per area (React / API / models)
- Test files spread throughout the codebase
- Security-sensitive code with audit logging requirements
- A team-shared slash command for code reviews
- A team-shared skill for codebase exploration
- Documented policy for plan mode vs direct execution
- Documented iterative refinement patterns

| Domain | Weight | Coverage in this scenario |
|---|---|---|
| **Domain 3** — Claude Code Configuration & Workflows | 20% | Full surface area |
| Domain 5 — Context Management | partial | `context: fork` mechanism |

Three sample questions from the exam (Q4, Q5, Q6) map directly to files
in this folder.

---

## Sample questions answered by this folder

| Sample Q | Tests | Lives in |
|---|---|---|
| Q4 — slash command location | Project vs user scope for commands | `.claude/commands/review.md` |
| Q5 — plan mode vs direct execution | Architectural complexity assessment | `.claude/CLAUDE.md` policy section |
| Q6 — applying conventions to test files | Glob patterns vs directory CLAUDE.md | `.claude/rules/testing.md` |

---

## Architecture at a glance

```
.claude/
├── CLAUDE.md                          ← always-loaded universal context
├── rules/                             ← path-scoped conditional context
│   ├── react.md                       ← loads for src/components/**
│   ├── api.md                         ← loads for src/api/**
│   ├── models.md                      ← loads for src/models/**
│   ├── testing.md                     ← loads for **/*.test.* and tests/**
│   └── security.md                    ← loads for auth*, encryption*, Session*
├── commands/                          ← developer-invoked shortcuts
│   └── review.md                      ← invoked by typing /review
└── skills/                            ← Claude-invoked workflows
    └── explore-codebase/
        └── SKILL.md                   ← uses context: fork for isolation
```

Four invocation patterns:

| Folder | Invocation | Loads when |
|---|---|---|
| `CLAUDE.md` | Automatic | Always |
| `rules/` | Automatic | File path matches glob |
| `commands/` | Explicit (`/<name>`) | Developer types the command |
| `skills/` | Autonomous | Claude decides relevant |

---

## The shared-vs-personal rule

> **`<repo>/.claude/` is SHARED with the team via git.**
> **`~/.claude/` is PERSONAL — only on your machine.**

For every config choice: *"Should every teammate get this when they
`git clone`?"*

- **Yes** → `<repo>/.claude/`
- **No** → `~/.claude/`

| Configuration | Goes in | Why |
|---|---|---|
| Team's React conventions | `.claude/rules/react.md` | Everyone needs them |
| `/review` slash command | `.claude/commands/review.md` | Everyone needs it |
| Personal verbosity preference | `~/.claude/CLAUDE.md` | Personal style |
| Team's MCP servers | `.mcp.json` | Everyone needs them |
| Experimental MCP server | `~/.claude.json` | Don't impose on team |

---

## Prerequisites

- Claude Code installed (`npm install -g @anthropic-ai/claude-code`)
- An Anthropic account configured with Claude Code
- PowerShell (Windows)
- VS Code recommended

No Python or virtual environment needed — this scenario has no agent code.

---

## Quick start

```powershell
cd scenario-02-claude-code-dev-workflow
code .
tree /F .claude
claude

# Inside Claude Code:
/memory
```

If `/memory` shows `.claude/CLAUDE.md` and the rule files load when
editing matching files, the configuration is wired correctly.

---

## Project layout

```
scenario-02-claude-code-dev-workflow/
├── README.md
│
├── .claude/                           # Claude Code configuration
│   ├── CLAUDE.md
│   ├── rules/
│   │   ├── react.md
│   │   ├── api.md
│   │   ├── models.md
│   │   ├── testing.md
│   │   └── security.md
│   ├── commands/
│   │   └── review.md
│   └── skills/
│       └── explore-codebase/
│           └── SKILL.md
│
├── src/                               # mock project files (scaffold only)
│   ├── components/
│   │   ├── Button.tsx
│   │   └── Button.test.tsx            # colocated test
│   ├── api/
│   │   └── orders.ts
│   ├── models/
│   │   └── User.ts
│   └── lib/
│       └── encryption.ts
│
├── tests/
│   └── integration/
│       └── orders.test.ts             # centralized test
│
├── package.json
└── tsconfig.json
```

The `src/` and `tests/` files are minimal — they provide the shapes
the configuration is scoped against, not a runnable application.

---

## The six milestones

### M1 — Mock project scaffold
Sets up `src/` and `tests/` for path-scoped rules to target.

### M2 — CLAUDE.md hierarchy with `@import`
**Tests Task 3.1 + 3.3.** Project-level `CLAUDE.md` shared via git;
user-level `~/.claude/CLAUDE.md` personal. `@import` splits a large
CLAUDE.md into area-specific rule files. Each rule has YAML frontmatter
with `paths:` globs controlling when it loads.

### M3 — Slash command + skill
**Tests Task 3.2. Maps to Sample Q4.** Commands in `.claude/commands/`
are developer-invoked. Skills in `.claude/skills/` are Claude-invoked.
The `explore-codebase` skill demonstrates:

- **`context: fork`** — inherits parent state snapshot, evolves
  independently, returns only the final summary. Verbose intermediate
  work stays in the fork.
- **`allowed-tools: [Read, Grep, Glob]`** — read-only filesystem access
  as a structural guarantee, not a prompt instruction.

### M4 — Path-scoped rules deep dive
**Tests Task 3.3. Maps to Sample Q6.** Test files spread throughout a
codebase need conventions that apply by filename pattern, not by
directory. Glob `**/*.test.tsx` catches both colocated tests and
centralized ones. A directory-scoped `tests/CLAUDE.md` silently misses
colocated tests.

The security rule extends this with patterns like `src/**/auth*.ts` —
applying conventions to files identified by what they are, not where
they live.

### M5 — Plan mode vs direct execution
**Tests Task 3.4. Maps to Sample Q5.** Plan mode for work where the
*plan* is the risky part (architectural changes, library migrations,
multi-file dependency analysis). Direct execution for well-scoped work
with clear correctness criteria.

Three exercises in this milestone:
1. Direct execution — fix one bug in one file
2. Plan mode — migrate zod to valibot (architectural)
3. Direct execution — add audit logging (feels complex but isn't)

### M6 — Iterative refinement techniques
**Tests Task 3.5.** Four techniques matched to symptoms:

- Inconsistent output shape → concrete I/O examples
- Subtle correctness criteria → test-driven iteration
- Unfamiliar domain → interview pattern
- Multiple fixes → bundle if interacting, sequence if independent

---

## Three exam-aligned exercises

### Exercise 1: Verify the configuration hierarchy

```powershell
claude
```

Inside Claude Code:
```
/memory
```

Then ask:
```
What conventions apply when I'm editing src/components/Button.tsx?
```

Then ask:
```
What conventions apply when I'm editing tests/integration/orders.test.ts?
```

The testing rules apply to both centralized and colocated test files
because the glob patterns match by filename, not directory.

### Exercise 2: Use the `/review` slash command

Make a deliberate violation in `src/components/Button.tsx` (an `any`
type or `console.log`). Then in Claude Code:

```
/review
```

The violation should be flagged because the project's CLAUDE.md rules
are loaded automatically.

### Exercise 3: Plan mode for an architectural change

Enter plan mode (`Shift+Tab` or `/plan`):

```
I need to migrate this project from zod to valibot. Map the scope and
propose an approach. Don't make changes yet.
```

Claude produces a structured plan. Review it, refine if needed, exit
plan mode, then execute the plan.

---

## Studying with this configuration

### 1. Read the files in order

1. `.claude/CLAUDE.md` — top of hierarchy
2. `.claude/rules/react.md` — simple path-scoped rule
3. `.claude/rules/testing.md` — multi-pattern case
4. `.claude/rules/security.md` — cross-cutting case
5. `.claude/commands/review.md` — slash command structure
6. `.claude/skills/explore-codebase/SKILL.md` — `context: fork` and `allowed-tools`

### 2. Stress-test the config by moving files

- Move `.claude/CLAUDE.md` → `~/.claude/CLAUDE.md`. Project conventions
  disappear. (Sample Q4 distractor B)
- Move `.claude/rules/testing.md` content into `tests/CLAUDE.md`.
  Colocated tests no longer match. (Sample Q6 distractor D)
- Remove `paths:` from `.claude/rules/react.md`. The rule loads on
  every edit, wasting tokens.

Each experiment maps to an exam distractor.

### 3. Re-read Sample Questions 4, 5, 6 with this config open

Each question's correct answer maps to a specific file in this folder.

---

## Common distractor patterns this config debunks

| Distractor | Why wrong | Reference file |
|---|---|---|
| Put a team command in `~/.claude/commands/` | Personal scope | `.claude/commands/review.md` |
| Consolidate everything in root CLAUDE.md | Bloats, loads everywhere | `@import` + `.claude/rules/*.md` |
| Use directory-level CLAUDE.md for tests | Misses colocated tests | `.claude/rules/testing.md` glob patterns |
| Skills should share parent context fully | Pollutes parent | `context: fork` in explore-codebase |
| Skills should have full toolset for flexibility | No architectural guarantee | `allowed-tools` restriction |
| Always use plan mode for safety | Unnecessary friction | CLAUDE.md plan-mode policy |
| Switch to plan mode only if complexity emerges | Complexity often stated upfront | Sample Q5 analysis |
| Bundle all fixes for efficiency | Drift risk for independent issues | M6 bundle-vs-sequence rule |

---

## The Domain 3 mental model in one paragraph

Claude Code configuration has four invocation patterns. `CLAUDE.md`
loads always — use it for universal standards. `.claude/rules/` loads
conditionally based on path globs — use it for area-specific conventions,
especially when the files are spread across directories.
`.claude/commands/` loads on developer invocation — use it for shortcuts
to common prompts. `.claude/skills/` loads on Claude's autonomous
decision — use it for reusable workflows, optionally with `context: fork`
and `allowed-tools` for isolation and restriction. Anything in
`<repo>/.claude/` is shared via git; anything in `~/.claude/` is personal.
Plan mode is for tasks where the plan is the risky part (architectural
decisions, multi-file changes, library migrations); direct execution
is for well-scoped changes with clear correctness criteria. Iterative
refinement matches symptoms to techniques: inconsistent output →
I/O examples; subtle correctness → test-driven; unfamiliar domain →
interview pattern; multiple fixes → bundle if interacting, sequence
if independent.

---

## Troubleshooting

### `/memory` doesn't show rule files

1. Verify `.claude/rules/*.md` files exist at the right paths.
2. Verify each is imported via `@import .claude/rules/X.md` in
   `.claude/CLAUDE.md`.
3. Path-scoped rules only load when editing a matching file. Open a
   relevant file (e.g., `src/components/Button.tsx`) and re-run `/memory`.

### `/review` doesn't appear in the command list

1. File must be at `.claude/commands/review.md` (case-sensitive).
2. YAML frontmatter must be well-formed (`---` delimiters, valid keys).
3. Run Claude Code from the scenario folder, not a parent.

### Skill doesn't get invoked

1. Ask explicitly: "Use the explore-codebase skill to map this project."
2. Verify the skill's `description:` clearly states what it does.
3. Check `/skills` (if your Claude Code version supports it).

### Conventions aren't being applied

1. Run `/memory` to see what's actually loaded.
2. Verify the file path matches a `paths:` glob in the rule file.
3. Verify the rule file is `@import`-ed in `.claude/CLAUDE.md`.
4. If loaded but not applied, the rule wording may be too soft.
   Strengthen with explicit "MUST" or add a concrete example.

---

## Where to go next

- **Scenario 3** (Multi-Agent Research System) — extends Scenario 1's
  agent loop with subagent orchestration via the Task tool
- **Scenario 5** (CI/CD with Claude Code) — extends this scenario into
  automated pipelines (Task 3.6)
- **Scenario 6** (Structured Data Extraction) — Domain 4 deep dive

---

## License

Study material derived from the Claude Certified Architect — Foundations
exam guide. Configuration patterns documented at
https://code.claude.com/docs/en/best-practices.