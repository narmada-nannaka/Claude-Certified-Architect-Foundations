---
description: Map an unfamiliar codebase to understand its structure, entry points, and key flows. Produces a summary report; intermediate exploration is isolated from the main session context.
context: fork
allowed-tools:
  - Read
  - Grep
  - Glob
argument-hint: <optional: starting file, package directory, or feature area to focus on>
---

# Explore Codebase

You are mapping an unfamiliar codebase. Your goal is to produce a
concise summary of the architecture, entry points, and key flows
that helps a developer get oriented quickly.

## Scope

If $ARGUMENTS was provided, focus your exploration on that area.
Otherwise, start at the repository root.

## Approach

Build understanding **incrementally**, not exhaustively. Per the
project's standards (and Task 2.5's pattern):

1. **Start with Glob** to identify file types and overall shape.
   Look for entry points (main.ts, index.ts, app.ts, server.ts).
   Get a rough count of files per area.

2. **Use Grep to find exports and key types.** Search for `export
   function`, `export class`, `export interface`. This reveals the
   public API without reading every file.

3. **Read entry points carefully.** Read the file from top to bottom.
   Note what it imports, what it exports, and what other files it
   triggers.

4. **Follow imports selectively.** Don't follow every import — only
   the ones that go to files you haven't seen yet AND that look
   architecturally significant (not utility imports like `lodash`).

5. **Stop when you have enough.** Aim for a summary, not a complete
   map. If you've identified the entry points, the major packages,
   and one representative flow, you have enough.

## Output

Produce a structured summary with this shape:

### Architecture
2-3 sentences on what kind of system this is and how it's organized.

### Entry points
Up to 3 entry-point files with one-line descriptions.

### Major areas
For each top-level source folder, one line on its purpose.

### Notable patterns
1-3 conventions you observed (e.g., "uses repository pattern for
DB access"; "API handlers return structured Result types"; "tests
are colocated").

### Suggested next reading
2-3 files a new developer should read next, with one-line reasons.

## What NOT to do

- Do NOT read every file. Aim for breadth-first understanding.
- Do NOT propose changes. This skill is purely exploratory.
- Do NOT load build configs, lockfiles, or generated files unless
  they're explicitly the focus area.
- Do NOT speculate about intent without evidence — if you don't
  know why something is structured a certain way, say so.