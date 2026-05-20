"""CLI runner for the full research pipeline.

Usage:
    python scripts/run_research.py "the impact of AI on creative industries"

Now uses the pipeline with iterative gap-fill refinement.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent.parent / ".env")

from src.pipeline import run_research_pipeline

def main():
    if len(sys.argv) < 2:
        topic = "the impact of AI on creative industries"
        print(f"No topic provided. Using default: {topic}")
    else:
        topic = " ".join(sys.argv[1:])

    print(f"\n=== Research pipeline: {topic} ===\n")
    result = run_research_pipeline(topic)

    print(f"Refinement iterations: {result.refinement_iterations}")
    if result.hit_iteration_cap:
        print("⚠ Hit iteration cap — some gaps remain unfilled")
    print(f"Total subagent invocations: {len(result.all_invocations)}")
    print(f"Total findings collected: {len(result.all_findings)}\n")

    print("--- Gap history across rounds ---")
    for i, gaps in enumerate(result.gap_history):
        if gaps:
            domains = [g["domain"] for g in gaps]
            print(f"  Round {i}: {len(gaps)} gaps → {domains}")
        else:
            print(f"  Round {i}: 0 gaps (terminated)")

    print("\n--- Initial vs gap-fill invocations ---")
    initial = [i for i in result.all_invocations if i.get("phase") != "gap_fill"]
    gap_fills = [i for i in result.all_invocations if i.get("phase") == "gap_fill"]
    print(f"  Initial investigation: {len(initial)}")
    print(f"  Gap-fill investigation: {len(gap_fills)}")

    if not result.final_report:
        print("\n(No final report produced.)")
        return

    print("\n=== Final Structured Report ===\n")
    print(f"TOPIC: {result.final_report['topic']}\n")
    print(f"EXECUTIVE SUMMARY: {result.final_report['executive_summary']}\n")

    print("DOMAIN SECTIONS:")
    for section in result.final_report["domain_sections"]:
        print(f"\n  [{section['domain']}]")
        for f in section["key_findings"][:3]:  # cap display
            print(f"    • {f['claim']}")
            print(f"      → {f['source_name']} ({f['publication_date_iso']})")

    if result.final_report["conflicts"]:
        print("\nCONFLICTS:")
        for c in result.final_report["conflicts"]:
            print(f"  • {c['topic']}")
            print(f"    A: {c['claim_a']} ({c['source_a']})")
            print(f"    B: {c['claim_b']} ({c['source_b']})")

    if result.final_report["coverage_gaps"]:
        print("\nREMAINING GAPS:")
        for g in result.final_report["coverage_gaps"]:
            print(f"  • {g['domain']}: {g['rationale']}")
    else:
        print("\n✓ All coverage gaps filled.")


if __name__ == "__main__":
    main()