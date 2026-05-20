"""CLI runner for the coordinator.

Usage:
    python scripts/run_research.py "the impact of AI on creative industries"

Watch the output to see:
- How the coordinator decomposes the topic
- Which subagents it invokes and with what prompts
- Whether it invokes them in parallel (multiple in one iteration)
- The total findings collected
"""
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
# Load from project root first, then fall back to the shared parent .env
load_dotenv(Path(__file__).parent.parent / ".env")
load_dotenv(Path(__file__).parent.parent.parent / ".env")

from src.coordinator import run_coordinator


def main():
    if len(sys.argv) < 2:
        topic = "the impact of AI on creative industries"
        print(f"No topic provided. Using default: {topic}")
    else:
        topic = " ".join(sys.argv[1:])

    print(f"\n=== Research session: {topic} ===\n")
    session = run_coordinator(topic)

    print(f"Coordinator iterations: {session.coordinator_run.iterations}")
    print(f"Subagent invocations: {len(session.subagent_invocations)}")
    print(f"Total findings collected: {len(session.all_findings)}\n")

    print("--- Subagent invocations ---")
    for i, inv in enumerate(session.subagent_invocations, 1):
        agent = inv["agent_name"]
        prompt_preview = inv["prompt"][:80].replace("\n", " ")
        if inv["result"].get("isError"):
            status = f"ERROR {inv['result'].get('errorCategory', '')}"
        else:
            status = f"{inv['result'].get('findings_count', 0)} findings"
        print(f"  {i}. [{agent}] {prompt_preview}... -> {status}")

    print("\n--- Domain coverage ---")
    domains = {}
    for f in session.all_findings:
        domains[f["domain"]] = domains.get(f["domain"], 0) + 1
    for domain, count in sorted(domains.items()):
        print(f"  {domain}: {count}")

    print("\n--- Coordinator's final message ---")
    print(session.coordinator_run.final_text)


if __name__ == "__main__":
    main()