"""Lab management: restart restores starter state; solve applies solutions."""
import shutil
import sys
from pathlib import Path

LAB_ROOT = Path(__file__).parent
OUTPUT_DIR = LAB_ROOT / "output"
PROMPTS_DIR = LAB_ROOT / "prompts"

STARTER_REVIEW_PROMPT = '''You are reviewing a pull request. Be thorough and check everything.

<checklist>
Check the following aspects:
- Bugs and logic errors
- Security issues
- Code style and formatting
- Variable and function naming
- Missing documentation and type hints
- Error handling patterns
</checklist>

<code_files>
{files_content}
</code_files>

<output_schema>
{output_schema}
</output_schema>

Respond with a JSON object matching the schema. For each issue, include
file, line, issue description, severity, category, confidence,
suggested_fix, and reasoning.
'''


def restart():
    """Restore starter state."""
    print("Restoring starter state...")
    (PROMPTS_DIR / "review_prompt.txt").write_text(STARTER_REVIEW_PROMPT, encoding="utf-8")
    if OUTPUT_DIR.exists():
        shutil.rmtree(OUTPUT_DIR)
    print("Done. Starter review_prompt.txt restored; output/ cleared.")


def solve():
    """Apply the refined prompt from Steps 4 + 5 combined."""
    print("Applying solution prompt with explicit criteria and few-shot examples...")
    # See README Step 4 + Step 5 for the full refined prompt
    print("Open prompts/review_prompt.txt and follow the README Steps 4 and 5.")
    print("(This solver is a placeholder — apply the prompt changes manually for learning.)")


def main():
    if len(sys.argv) != 2:
        print("Usage: python manage.py {restart|solve}")
        sys.exit(1)
    cmd = sys.argv[1]
    if cmd == "restart":
        restart()
    elif cmd == "solve":
        solve()
    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)


if __name__ == "__main__":
    main()