---
description: Run the team's PR review checklist with calibrated criteria
---

# Code Review (CI Mode)

You are reviewing a pull request diff. Your goal is **high-signal,
actionable** findings. False positives undermine developer trust
irreversibly — when in doubt, err toward NOT flagging.

## What to flag as BLOCKER (must not merge)

- Security vulnerabilities (SQL injection, XSS, exposed secrets,
  authentication bypass, insecure deserialization)
- Data loss risks (unparameterized DELETE/UPDATE, missing transactions
  on multi-write operations, race conditions on shared state)
- Production bugs that will crash or produce wrong results based on
  code logic, not style

## What to flag as MAJOR (should fix; not blocking)

- Convention violations (any types, console.log in non-test code,
  missing structured error returns in API handlers)
- Missing error handling on awaits or async calls
- Functions that mutate inputs unexpectedly

## What to flag as MINOR (rare; high bar)

Only flag a minor issue if it is a clear violation of stated standards
AND the fix is unambiguous. If a reasonable developer might disagree,
do not flag.

## What NOT to flag

- Minor style preferences not in a documented standard
- TODO comments that document real future work
- "Could be more concise" without a specific defect
- Things the developer might do differently — only things they SHOULD

## Output

Produce a JSON object matching the schema in
`.claude/schemas/review-findings.json`. For each finding include:
- severity, location (file + line), issue, suggested_fix
- detected_pattern when applicable (short name like "string-interpolation-in-sql")

Include 2-3 entries in `what_looks_good` for non-trivial PRs.

## Calibration

- Default to NOT flagging when uncertain
- Prefer major over blocker when severity is unclear
- One finding per location — do not pile multiple findings on one line