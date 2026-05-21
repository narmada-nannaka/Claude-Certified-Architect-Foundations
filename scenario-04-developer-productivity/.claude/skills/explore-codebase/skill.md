---
description: Map an unfamiliar codebase and persist detailed findings to a scratchpad for follow-up questions.
context: fork
allowed-tools:
  - Read
  - Grep
  - Glob
  - Write
argument-hint: <optional: starting file, package, or feature area>
---

# Explore Codebase (with Scratchpad)

You are mapping an unfamiliar codebase. Your goal is to produce a
concise summary for the main session AND persist detailed findings
to a scratchpad file so the developer can ask follow-up questions
that reference your discovery without you needing to re-explore.

## Scope

If $ARGUMENTS was provided, focus your exploration there. Otherwise,
start at the repository root.

## Approach: incremental narrowing

Per Task 2.5's pattern, build understanding incrementally:

1. **Start with Glob** to identify file types and overall shape.
   Look for entry points (main.ts, index.ts, app.ts, server.ts).
   Count files per area to gauge scale.

2. **Use Grep to find exports and key types.** Search for `export
   function`, `export class`, `export interface`. This surfaces
   the public API without reading every file.

3. **Read entry points carefully.** Top to bottom. Note imports
   and exports.

4. **Follow imports selectively.** Only the ones that go to files
   you haven't seen AND look architecturally significant. Skip
   utility imports like `lodash`, `zod`, etc.

5. **Stop at sufficient understanding.** Aim for orientation, not
   completeness.

## Scratchpad persistence

BEFORE returning your summary, write your detailed findings to
`.claude/scratch/explore-<short-timestamp>.md` with this structure:

Codebase Exploration: <topic from arguments or "full codebase">
Date: <ISO 8601>
Files inspected
<file paths and one-line per file what you learned from each>
Entry points
<each entry point with its key imports and exports>
Symbol map
<important functions, classes, types and where defined>
Notable patterns
<conventions and architectural observations>
Open questions
<things you noticed but didn't pursue>

The scratchpad is the durable record. The summary you return to
the main session is the executive view of it.

## Output (returned to main session)

After writing the scratchpad, return a structured summary:

### Architecture
2-3 sentences on what kind of system this is.

### Entry points
Up to 3 entry-point files with one-line descriptions.

### Major areas
For each top-level source folder, one line on its purpose.

### Notable patterns
1-3 conventions observed.

### Scratchpad location
The path to the scratchpad file you wrote. Mention that follow-up
questions can reference the scratchpad without you re-exploring.

### Suggested next reading
2-3 files a new developer should read next, with one-line reasons.

## What NOT to do

- Do not read every file. Breadth-first understanding.
- Do not propose changes. This skill is exploratory only.
- Do not load build configs or generated files unless explicitly
  in the focus area.
- Do not speculate about intent without evidence.