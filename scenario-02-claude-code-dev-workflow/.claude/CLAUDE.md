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

## When proposing changes

- For changes touching more than 5 files, enter plan mode before making
  edits. This is non-negotiable for cross-cutting changes.
- Test files must be updated in the same commit as the code they test.
- Never modify generated files (e.g., `*.gen.ts`, anything under `dist/`).

## How to ask for help

If a question is ambiguous, use the interview pattern: ask 2-3 clarifying
questions before implementing. Don't guess on requirements that affect
more than one file.