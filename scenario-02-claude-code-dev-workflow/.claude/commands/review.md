---
description: Run the team's PR review checklist against the current changes
argument-hint: <optional: specific file or PR number to focus on>
---

# Code Review

You are running the team's standard code review checklist. Apply the
project's coding conventions (loaded from `.claude/CLAUDE.md` and the
path-scoped rules in `.claude/rules/`) and produce a structured review.

## What to review

If an argument was provided, focus the review on $ARGUMENTS.
Otherwise, review all uncommitted changes (staged and unstaged).

For each file changed, examine:

1. **Correctness** — does the code do what its name and comments claim?
2. **Conventions** — does it follow the path-scoped rules for its area?
3. **Tests** — is there a corresponding test file? Are the tests
   exercising the new behavior or just the happy path?
4. **Side effects** — does it introduce side effects that aren't
   documented in the function signature or docstring?

## What to skip

Do NOT report on:

- Minor style preferences that don't violate a stated convention
- Code style decisions documented as accepted in `.claude/rules/`
- Auto-generated files (anything matching `*.gen.ts` or under `dist/`)

## Output format

Produce a single structured review with this shape:

### Summary
One paragraph describing the change at a high level and your overall
recommendation (approve / approve with comments / request changes).

### Findings
For each issue, use this format:

- **Severity**: blocker | major | minor
- **Location**: file path and line number
- **Issue**: what's wrong
- **Suggested fix**: a concrete change (not "consider refactoring")

Group findings by severity, blockers first.

### What looks good
2-3 bullet points highlighting decisions that are well-made. Reviews
that are only negative damage developer trust; calibrated reviews
include praise for genuine craftsmanship.

## Calibration notes

- A finding marked "blocker" means the code should NOT be merged as-is.
- "Major" means worth fixing but doesn't block merge.
- "Minor" should be rare — if you're routinely producing minor findings,
  you're being noisier than the team needs. Aim for high signal.