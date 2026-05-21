## Built-in tool selection

Use the Claude Code-native tools in preference to Bash equivalents
unless Bash is genuinely needed (execution, git operations, system
queries).

- **Glob** for finding files by path pattern (e.g., `**/*.test.ts`)
- **Grep** for finding content within files (e.g., import statements,
  function references, error messages)
- **Read** to load a full file's contents
- **Edit** to modify a unique text fragment in a file
- **Read + Write** when Edit's unique-match requirement isn't met
- **Bash** for execution: running tests, git commands, build scripts

For exploring an unfamiliar codebase, start with Grep on the target
symbol, then Read its containing file(s), then Grep the broader
surface. Do not read all files upfront — context budget is finite.