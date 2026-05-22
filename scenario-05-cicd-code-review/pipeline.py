"""CI Code Review Pipeline Simulator.

Simulates a CI runner invoking Claude Code in non-interactive mode (-p)
against a pull request. Demonstrates:
- Step 3: single-pass review with vague prompt
- Step 6: multi-pass review (per-file + cross-file integration)
- Step 7: independent reviews compared
"""
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# Terminal colors
RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
RED = "\033[31m"
CYAN = "\033[36m"

LAB_ROOT = Path(__file__).parent
PR_FILES_DIR = LAB_ROOT / "pr_files"
PROMPTS_DIR = LAB_ROOT / "prompts"
OUTPUT_DIR = LAB_ROOT / "output"

SOURCE_FILES = ["auth.py", "orders.py", "utils.py"]  # exclude test_utils.py


def get_source_files():
    return SOURCE_FILES


def load_single_file(filename: str) -> str:
    """Load one PR file as a labeled string for the prompt."""
    path = PR_FILES_DIR / filename
    content = path.read_text(encoding="utf-8")
    return f"--- FILE: {filename} ---\n{content}\n"


def load_pr_files() -> str:
    """Load all source PR files concatenated for a single-pass review."""
    parts = []
    for filename in SOURCE_FILES:
        parts.append(load_single_file(filename))
    return "\n".join(parts)


def load_schema() -> str:
    """Load the review schema as a JSON string."""
    return (LAB_ROOT / "review_schema.json").read_text(encoding="utf-8")


def load_review_prompt() -> str:
    return (PROMPTS_DIR / "review_prompt.txt").read_text(encoding="utf-8")


def load_integration_prompt() -> str:
    return (PROMPTS_DIR / "integration_prompt.txt").read_text(encoding="utf-8")


def build_review_prompt(files_content: str) -> str:
    """Build the full review prompt with files and schema injected."""
    template = load_review_prompt()
    schema = load_schema()
    return template.replace("{files_content}", files_content).replace(
        "{output_schema}", schema
    )


def run_claude_review(prompt: str) -> dict:
    """Invoke claude -p --output-format json and parse the result."""
    try:
        result = subprocess.run(
            ["claude", "-p", prompt, "--output-format", "json"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=300,
        )
    except subprocess.TimeoutExpired:
        print(f"{RED}Claude Code timed out after 5 minutes.{RESET}")
        return None
    except FileNotFoundError:
        print(f"{RED}claude command not found. Is Claude Code installed?{RESET}")
        return None

    if result.returncode != 0:
        print(f"{RED}Claude Code exited with code {result.returncode}{RESET}")
        print(f"{DIM}stderr: {result.stderr[:500]}{RESET}")
        return None

    # The --output-format json envelope contains the result text
    try:
        envelope = json.loads(result.stdout)
    except json.JSONDecodeError:
        print(f"{RED}Could not parse Claude Code envelope as JSON.{RESET}")
        print(f"{DIM}stdout: {result.stdout[:500]}{RESET}")
        return None

    # The actual review response is in the "result" field of the envelope
    review_text = envelope.get("result", "")
    if not review_text:
        print(f"{RED}Envelope has no 'result' field.{RESET}")
        return None

    # Strip any markdown fences the model may have added
    review_text = review_text.strip()
    if review_text.startswith("```"):
        # Remove first line (```json or ```) and last line (```)
        lines = review_text.split("\n")
        if len(lines) > 2:
            review_text = "\n".join(lines[1:-1])

    try:
        return json.loads(review_text)
    except json.JSONDecodeError as e:
        print(f"{RED}Review response is not valid JSON: {e}{RESET}")
        print(f"{DIM}Review text first 500 chars: {review_text[:500]}{RESET}")
        return None


def save_review(review: dict) -> Path:
    """Save the review with a timestamp."""
    OUTPUT_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    path = OUTPUT_DIR / f"review-{timestamp}.json"
    path.write_text(json.dumps(review, indent=2), encoding="utf-8")
    return path


def load_latest_review() -> dict:
    """Load the most recent review for comparison."""
    if not OUTPUT_DIR.exists():
        return None
    files = sorted(OUTPUT_DIR.glob("review-*.json"))
    if not files:
        return None
    return json.loads(files[-1].read_text(encoding="utf-8"))


def display_review(review: dict):
    """Pretty-print the review findings to the terminal."""
    findings = review.get("findings", [])
    print(f"\n{BOLD}Review Findings ({len(findings)}){RESET}\n")

    if not findings:
        print(f"{DIM}No findings reported.{RESET}\n")
        return

    for i, f in enumerate(findings, 1):
        severity = f.get("severity", "?")
        sev_color = {
            "critical": RED,
            "warning": YELLOW,
            "info": DIM,
        }.get(severity, "")
        category = f.get("category", "?")
        confidence = f.get("confidence", "?")
        file_loc = f"{f.get('file', '?')}:{f.get('line', '?')}"

        print(f"{BOLD}{i}. [{sev_color}{severity}{RESET}{BOLD}] "
              f"({category}, conf={confidence}) {file_loc}{RESET}")
        print(f"   {f.get('issue', '')}")
        if f.get('suggested_fix'):
            print(f"   {DIM}Fix: {f['suggested_fix']}{RESET}")
        if f.get('reasoning'):
            print(f"   {DIM}Why: {f['reasoning']}{RESET}")
        print()


def compare_reviews(previous: dict, current: dict):
    """Compare current review to previous, summarizing the delta."""
    if not previous:
        print(f"{DIM}No previous review to compare against.{RESET}\n")
        return

    prev_count = len(previous.get("findings", []))
    curr_count = len(current.get("findings", []))
    delta = curr_count - prev_count

    print(f"{BOLD}Delta vs previous review:{RESET}")
    print(f"  Previous: {prev_count} findings")
    print(f"  Current:  {curr_count} findings")
    arrow = "↓" if delta < 0 else ("↑" if delta > 0 else "→")
    print(f"  Change:   {arrow} {abs(delta)}\n")


def run_single_pass():
    """Step 3 / 4 / 5: single-pass review of all files together."""
    print(f"\n{BOLD}Single-Pass Review{RESET}\n")
    previous = load_latest_review()
    files_content = load_pr_files()
    prompt = build_review_prompt(files_content)
    review = run_claude_review(prompt)
    if review is None:
        return
    save_review(review)
    display_review(review)
    compare_reviews(previous, review)


def run_multi_pass():
    """Step 6: per-file passes plus a cross-file integration pass."""
    print(f"\n{BOLD}Multi-Pass Review{RESET}\n")

    previous = load_latest_review()
    source_files = get_source_files()
    all_findings = []

    # Phase 1: per-file local passes
    total_passes = len(source_files) + 1
    for i, filename in enumerate(source_files, 1):
        print(f"{DIM}Pass {i}/{total_passes}: Reviewing {filename}...{RESET}")
        file_content = load_single_file(filename)
        prompt = build_review_prompt(file_content)
        review = run_claude_review(prompt)
        if review and review.get("findings"):
            all_findings.extend(review["findings"])

    # Phase 2: cross-file integration pass
    print(f"{DIM}Pass {total_passes}/{total_passes}: Cross-file integration...{RESET}")
    files_content = load_pr_files()
    findings_json = json.dumps(all_findings, indent=2)
    schema = load_schema()
    template = load_integration_prompt()
    integration_prompt = (template
        .replace("{per_file_findings}", findings_json)
        .replace("{files_content}", files_content)
        .replace("{output_schema}", schema))
    integration_review = run_claude_review(integration_prompt)
    if integration_review:
        cross_findings = integration_review.get("findings", [])
        all_findings.extend(cross_findings)

    combined = {
        "findings": all_findings,
        "summary": (
            f"Multi-pass: {len(source_files)} per-file + 1 integration, "
            f"{len(all_findings)} total findings"
        ),
    }
    save_review(combined)
    display_review(combined)
    compare_reviews(previous, combined)


def run_independent_review():
    """Step 7: two independent reviews compared."""
    print(f"\n{BOLD}Independent Review Comparison{RESET}\n")

    previous = load_latest_review()
    files_content = load_pr_files()
    prompt = build_review_prompt(files_content)

    print(f"{DIM}Running review instance 1...{RESET}")
    review_1 = run_claude_review(prompt)
    print(f"{DIM}Running review instance 2...{RESET}")
    review_2 = run_claude_review(prompt)

    if not review_1 or not review_2:
        print(f"{RED}One or both reviews failed.{RESET}\n")
        return

    findings_1 = review_1.get("findings", [])
    findings_2 = review_2.get("findings", [])
    keys_1 = set(f"{f.get('file', '')}:{f.get('line', '')}" for f in findings_1)
    keys_2 = set(f"{f.get('file', '')}:{f.get('line', '')}" for f in findings_2)

    common = keys_1 & keys_2
    only_1 = keys_1 - keys_2
    only_2 = keys_2 - keys_1

    print(f"\n{BOLD}Comparison:{RESET}")
    print(f"  {GREEN}Both found:{RESET}      {len(common)} finding(s)")
    print(f"  {YELLOW}Only reviewer 1:{RESET} {len(only_1)} finding(s)")
    print(f"  {YELLOW}Only reviewer 2:{RESET} {len(only_2)} finding(s)")

    if only_2:
        print(f"\n{BOLD}Unique from reviewer 2:{RESET}")
        for f in findings_2:
            key = f"{f.get('file', '')}:{f.get('line', '')}"
            if key in only_2:
                print(f"  {f.get('file')}:{f.get('line')} — {f.get('issue', '')}")
    print()

    unique_from_2 = [
        f for f in findings_2
        if f"{f.get('file', '')}:{f.get('line', '')}" in only_2
    ]
    all_findings = findings_1 + unique_from_2
    combined = {
        "findings": all_findings,
        "summary": f"Independent review: {len(all_findings)} combined findings",
    }
    save_review(combined)
    compare_reviews(previous, combined)


def format_as_pr_comments():
    """Step 7 follow-up: format the latest review as PR comments."""
    review = load_latest_review()
    if not review:
        print(f"{RED}No review available. Run a review first.{RESET}")
        return

    findings = review.get("findings", [])
    if not findings:
        print(f"{DIM}No findings to format as comments.{RESET}")
        return

    print(f"\n{BOLD}PR Comments (formatted by confidence){RESET}\n")
    high = [f for f in findings if f.get("confidence") == "high"]
    medium = [f for f in findings if f.get("confidence") == "medium"]
    low = [f for f in findings if f.get("confidence") == "low"]

    if high:
        print(f"{BOLD}{RED}BLOCKING (high confidence):{RESET}")
        for f in high:
            print(f"  - {f.get('file')}:{f.get('line')} [{f.get('severity')}] {f.get('issue')}")
        print()
    if medium:
        print(f"{BOLD}{YELLOW}REVIEW REQUIRED (medium confidence):{RESET}")
        for f in medium:
            print(f"  - {f.get('file')}:{f.get('line')} [{f.get('severity')}] {f.get('issue')}")
        print()
    if low:
        print(f"{BOLD}{DIM}INFORMATIONAL (low confidence):{RESET}")
        for f in low:
            print(f"  - {f.get('file')}:{f.get('line')} [{f.get('severity')}] {f.get('issue')}")
        print()


def main():
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print(f"{RED}ANTHROPIC_API_KEY not set. Check your .env file.{RESET}")
        sys.exit(1)

    while True:
        print(f"\n{BOLD}CI Code Review Pipeline{RESET}")
        print(f"  1. Single-pass review (Steps 3, 4, 5)")
        print(f"  2. Multi-pass review (Step 6)")
        print(f"  3. Independent review comparison (Step 7)")
        print(f"  4. Format last review as PR comments")
        print(f"  q. Quit")
        choice = input(f"\n{BOLD}Choice:{RESET} ").strip().lower()

        if choice == "1":
            run_single_pass()
        elif choice == "2":
            run_multi_pass()
        elif choice == "3":
            run_independent_review()
        elif choice == "4":
            format_as_pr_comments()
        elif choice in ("q", "quit", "exit"):
            print("Bye.")
            break
        else:
            print(f"{RED}Unknown choice: {choice}{RESET}")


if __name__ == "__main__":
    main()