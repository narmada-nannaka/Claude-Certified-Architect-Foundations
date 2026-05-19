# Project Configuration for Claude Code

This file is loaded automatically by Claude Code when working in this
repository. It applies to all developers who clone or pull this repo.

## What this project is

A mixed-convention TypeScript/React application with three architectural
areas:

- `src/components/` — React UI components (functional, hooks-based)
- `src/api/` — API handlers (async/await with structured error returns)
- `src/models/` — Database access (repository pattern)

Test files live in two places: colocated with source (`Button.test.tsx`
next to `Button.tsx`) and in `tests/integration/` for cross-module tests.

## Universal coding standards

These apply across the whole codebase, regardless of which area you're
editing. Area-specific rules are imported below.

- TypeScript strict mode is on. Do not introduce `any` types; use `unknown`
  if the type is truly indeterminate at a boundary.
- Async functions must handle errors explicitly. Either return a structured
  result (see API handler conventions) or throw a typed error — never let
  rejected promises propagate silently.
- Imports are absolute from `src/`, not relative-with-dots. Use
  `import { X } from "src/lib/y"`, not `import { X } from "../../lib/y"`.
- No console.log in committed code. Use the `logger` from `src/lib/logger`.

## Area-specific conventions

The following rules are imported from `.claude/rules/`. Each one applies
based on its declared `paths:` glob patterns — see each file for details.

@import .claude/rules/react.md
@import .claude/rules/api.md
@import .claude/rules/models.md
@import .claude/rules/testing.md
@import .claude/rules/security.md

## When to use plan mode vs direct execution

Plan mode is required for tasks where the answer to "how should this be
done?" isn't obvious. Use plan mode when:

- The change touches more than 5 files OR introduces architectural
  boundaries (new services, new modules, new shared abstractions).
- Multiple valid approaches exist and the right choice depends on
  team conventions, performance characteristics, or future flexibility.
- The work involves dependency analysis (e.g., "what else uses this
  function?") that determines scope.
- The work is a library migration, framework swap, or schema change.
- The request is under-specified ("add caching to the API layer") and
  the design choices are part of the task.

Direct execution is preferred when:

- The change is well-scoped (one file or an obviously-related cluster).
- The implementation approach is unambiguous from the request.
- Tests, lint, or type-check provide a clear correctness criterion.
- The blast radius of a wrong attempt is small.

When in doubt, default to plan mode for the planning phase, then
explicitly transition to direct execution to carry out the plan. Don't
try to stay in plan mode through the execution — it disables write
tools and exists specifically to be a separate phase.

## How to ask for help

If a question is ambiguous, use the interview pattern: ask 2-3 clarifying
questions before implementing. Don't guess on requirements that affect
more than one file.