"""CLI runner for the coordinator + synthesis pipeline.

Usage:
    python scripts/run_research.py "the impact of AI on creative industries"

Now runs through to synthesis, producing the full structured report.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent.parent / ".env")

from src.coordinator import run_coordinator
from src.synthesis import run_synthesis


def main():
    if len(sys.argv) < 2:
        topic = "the impact of AI on creative industries"
        print(f"No topic provided. Using default: {topic}")
    else:
        topic = " ".join(sys.argv[1:])

    print(f"\n=== Research session: {topic} ===\n")

    # Stage 1: coordinator investigates
    print("Stage 1: coordinator decomposes and delegates...\n")
    session = run_coordinator(topic)

    print(f"Coordinator iterations: {session.coordinator_run.iterations}")
    print(f"Subagent invocations: {len(session.subagent_invocations)}")
    print(f"Total findings: {len(session.all_findings)}")
    print(f"Domains covered: {sorted({f['domain'] for f in session.all_findings})}\n")

    if not session.all_findings:
        print("No findings collected. Cannot proceed to synthesis.")
        return

    # Stage 2: synthesis
    print("Stage 2: synthesis agent produces structured report...\n")
    result = run_synthesis(topic, session.all_findings)

    if result.is_error:
        print(f"Synthesis failed: {result.error_detail}")
        return

    print("=== Structured Report ===\n")
    print(f"TOPIC: {result.report['topic']}\n")
    print(f"EXECUTIVE SUMMARY: {result.report['executive_summary']}\n")

    print("DOMAIN SECTIONS:")
    for section in result.report["domain_sections"]:
        print(f"\n  [{section['domain']}]")
        for f in section["key_findings"]:
            print(f"    • {f['claim']}")
            print(f"      -> {f['source_name']} ({f['publication_date_iso']})")

    if result.report["conflicts"]:
        print("\nCONFLICTS:")
        for c in result.report["conflicts"]:
            print(f"  • {c['topic']}")
            print(f"    A: {c['claim_a']} ({c['source_a']}, {c.get('date_a', '')})")
            print(f"    B: {c['claim_b']} ({c['source_b']}, {c.get('date_b', '')})")
            if c.get("resolution_note"):
                print(f"    Note: {c['resolution_note']}")

    if result.report["coverage_gaps"]:
        print("\nCOVERAGE GAPS:")
        for g in result.report["coverage_gaps"]:
            print(f"  • {g['domain']}: {g['rationale']}")
    else:
        print("\n(No coverage gaps identified.)")


if __name__ == "__main__":
    main()