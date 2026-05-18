---
description: Conventions for test files (colocated and in tests/)
paths:
  - "**/*.test.ts"
  - "**/*.test.tsx"
  - "tests/**/*.ts"
---

# Testing conventions

These rules apply to ALL test files, regardless of location. This is
important because test files in this project live in two places:
colocated with source (`Button.test.tsx`) and centralized
(`tests/integration/*.test.ts`).

## Framework

Use Vitest's `describe`/`it` style. Do not introduce Jest, Mocha, or
other frameworks.

## Naming

- Test files mirror the file they test: `Button.tsx` → `Button.test.tsx`.
- `describe` blocks name the unit under test: `describe("Button", ...)`.
- `it` blocks describe behavior in present tense: `it("calls onClick when clicked", ...)`.

## Structure

- Arrange-Act-Assert pattern with whitespace separating the three.
- Mock setup happens inside `beforeEach`, not at the top of the file.
- Each test must be independent — no shared state between `it` blocks.

## What to test

- For React components: behavior, not implementation. Test what the user
  sees, not which hooks are called.
- For API handlers: every error category path plus the success path.
- For repositories: query construction, not database behavior (use mocks).