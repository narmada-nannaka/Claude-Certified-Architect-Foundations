# Project Standards

This project uses Claude Code in CI to review pull requests. The
review uses the criteria in `.claude/commands/review.md` and produces
output matching `.claude/schemas/review-findings.json`.

## Coding standards

- No `any` types in TypeScript. Use `unknown` and narrow if necessary.
- Async functions must handle errors explicitly. Never let rejected
  promises propagate silently.
- API handlers return structured results, never throw to callers.
- Logging goes through `logger`, not `console.log`.
- All SQL queries must be parameterized. Never interpolate user input.

## API selection for automated workflows

Match the API to whether something is waiting on the result.

| Workflow | API | Why |
|---|---|---|
| Pre-merge PR review | Synchronous | Developer is blocked; need result in CI time |
| Pre-deploy security scan | Synchronous | Deploy is blocked |
| Weekly tech debt report | Message Batches | Nobody waiting; 50% cost savings |
| Nightly test generation | Message Batches | Latency tolerant |
| Monthly architectural audit | Message Batches | Long analysis, no SLA |

For batch workflows: use `custom_id` for request/response correlation,
plan for up to 24-hour completion, resubmit only failed documents on
retry.