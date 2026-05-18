---
description: Conventions for database models
paths:
  - "src/models/**/*.ts"
---

# Database model conventions

These rules apply when editing files under `src/models/`.

## Repository pattern

Database access goes through `<Entity>Repository` classes:

- Method names follow `find<By><Criterion>` (e.g., `findByEmail`,
  `findById`).
- Methods that may return zero rows return `Entity | null`.
- Methods that return collections return `Entity[]` (never null).

## Queries

- Use Drizzle ORM for all queries; do not write raw SQL.
- Parameterize all user input — never interpolate strings into queries.
- Index hints are managed at the schema level, not in repository code.

## Transactions

- Multi-write operations must use explicit transactions.
- Transactions follow the pattern:
```typescript
  await db.transaction(async (tx) => { ... });
```