---
description: Conventions for API handlers
paths:
  - "src/api/**/*.ts"
---

# API handler conventions

These rules apply when editing files under `src/api/`.

## Error handling

API handlers MUST return structured results in this shape:

```typescript
type Result<T> =
  | { ok: true; data: T }
  | { ok: false; errorCategory: "transient" | "validation" | "permission"; message: string };
```

- Never throw from API handlers; always return a `Result`.
- The `errorCategory` field follows the same taxonomy as Scenario 1's
  hooks: transient (retryable), validation (input bug), permission
  (auth issue).

## Input validation

- Use `zod` schemas for all incoming data validation.
- Define the schema next to the handler that uses it.
- Validation failures return `{ ok: false, errorCategory: "validation", ... }`.

## External fetches

- Always specify a timeout (default: 5 seconds).
- Map 5xx responses to `errorCategory: "transient"`, 4xx to `"validation"`,
  401/403 to `"permission"`.
- Never log full request bodies — they may contain PII.