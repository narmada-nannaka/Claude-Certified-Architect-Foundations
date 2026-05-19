---
description: Conventions for security-sensitive code (auth, encryption, PII handling)
paths:
  - "src/**/auth*.ts"
  - "src/**/encryption*.ts"
  - "src/**/session*.ts"
  - "src/**/*secret*.ts"
  - "src/**/Session*.ts"
---

# Security-sensitive code conventions

These rules apply to files that handle authentication, encryption, sessions,
or any data flagged as security-sensitive. The patterns above match the
team's current naming conventions; if you create a new security-sensitive
file with a different name, add its path here.

## Logging

- Never log credentials (passwords, tokens, API keys, session IDs).
- Never log full request/response bodies that may contain credentials.
- When logging an error from a security-sensitive operation, log the
  error category and a request correlation ID, not the underlying cause.

## Error handling

- Authentication failures must return a generic error message to the
  caller ("invalid credentials"). Specific reasons (account locked,
  password expired, MFA required) live in internal logs only.
- Distinguish in code between "authentication failed" and "operation
  not permitted." A 401 vs 403 distinction matters for security
  monitoring.

## Secrets

- Never hard-code secrets, API keys, or credentials in this code.
- Read them from environment variables or a secrets manager.
- When in doubt, refuse to commit and flag the file for review.

## Audit logging

Every security-sensitive operation must produce an audit log entry with:

- `userId` or `sessionId` (whichever identifies the actor)
- `action` (login, logout, password_change, token_refresh, etc.)
- `outcome` (success | failure | partial)
- `timestamp_iso` (ISO 8601 UTC)
- `correlation_id` (request-level UUID)

The audit log is separate from the application log and has different
retention and access controls.

## Testing

Tests for security-sensitive code must:
- Cover failure paths as thoroughly as success paths
- Include explicit tests for credential leakage in error messages
- Never use real production credentials in test data — use clearly-fake
  fixtures (consistent with the broader testing rules)