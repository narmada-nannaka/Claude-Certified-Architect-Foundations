# CI Code Review Lab

This is a simulated CI pipeline. The pipeline runs `claude -p` to invoke
Claude Code in non-interactive mode against pull request files in
`pr_files/`. The review prompt lives in `prompts/review_prompt.txt` and
is iteratively refined across the lab steps.

## Review philosophy

- Default to NOT flagging when uncertain
- High false positive rates undermine developer trust irreversibly
- Genuine bugs and security issues only — skip style and naming opinions

## Review output

All findings conform to `review_schema.json`. Each finding includes
file, line, issue, severity, category, confidence, suggested_fix, and
reasoning.

## Severity definitions

- **critical**: will cause incorrect behavior or security vulnerability
  in production
- **warning**: could cause issues under specific conditions or edge cases
- **info**: improvement suggestion, low risk if not addressed