"""Interactive demo for the customer support agent.

Usage:
    python scripts/run_demo.py

Type messages and watch the agent's tool calls and responses. Useful
for exploring loop behavior, testing escalation, and triggering the
prerequisite-gate violation that Milestone 5 will fix.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.agent import run_agent


def print_run(run):
    print(f"\n[iterations: {run.iterations}, stop_reason: {run.stop_reason}]")
    for tc in run.tool_calls:
        if tc.get("blocked_by_gate"):
            tag = "BLOCKED " + tc["result"]["errorCategory"]
        elif tc["result"].get("isError"):
            tag = "ERROR " + tc["result"].get("errorCategory", "")
        else:
            tag = "ok"
        print(f"  → {tc['name']}({_short_input(tc['input'])}) [{tag}]")
    if run.gate_violations:
        print(f"  ⚠ gate violations this turn: {len(run.gate_violations)}")
    print(f"\nAgent: {run.final_text}")


def _short_input(d: dict) -> str:
    """Render input args compactly for the transcript."""
    return ", ".join(f"{k}={v!r}" for k, v in d.items())


def main():
    history = []
    session = None #created on first call
    print("Customer Support Agent demo. Type 'quit' to exit.\n")
    while True:
        try:
            user = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not user or user.lower() in {"quit", "exit"}:
            break

        run, history, session = run_agent(user, history, session)
        print_run(run)


if __name__ == "__main__":
    main()