"""Demo of error propagation + verify_fact in action.

Run with: python scripts/demo_failure_recovery.py

This script:
1. Configures the web_research subagent to "fail" with a timeout.
2. Runs the coordinator on a research topic.
3. Shows how the coordinator handles the structured error and recovers
   by delegating to document_analysis instead.
4. Runs synthesis, demonstrating verify_fact being called for a simple
   date lookup vs. a complex statistic being deferred.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent.parent / ".env")

from src import subagents
from src.pipeline import run_research_pipeline


def main():
    topic = "the impact of AI on writing and journalism"

    print(f"=== Demo: failure recovery + scoped verify_fact ===\n")
    print(f"Topic: {topic}")
    print(f"Simulating: web_research subagent will time out.\n")

    # Configure simulated failure for the web_research subagent
    subagents.SIMULATED_FAILURES["web_research"] = "timeout"

    try:
        result = run_research_pipeline(topic)
    finally:
        # Always clean up the simulation config
        subagents.SIMULATED_FAILURES.clear()

    print("--- Invocation summary ---")
    web_calls = [i for i in result.all_invocations if i["agent_name"] == "web_research"]
    doc_calls = [i for i in result.all_invocations if i["agent_name"] == "document_analysis"]
    web_failed = [i for i in web_calls if i["result"].get("isError")]

    print(f"Web research invocations: {len(web_calls)} (failed: {len(web_failed)})")
    print(f"Document analysis invocations: {len(doc_calls)}")
    print(f"Total findings collected: {len(result.all_findings)}\n")

    if web_failed:
        first_failure = web_failed[0]["result"]
        print("Example of structured error from web_research:")
        print(f"  isError: {first_failure['isError']}")
        print(f"  errorCategory: {first_failure['errorCategory']}")
        print(f"  isRetryable: {first_failure['isRetryable']}")
        print(f"  attempted_prompt: {first_failure['attempted_prompt'][:80]}...")
        print(f"  coverage_note: {first_failure['coverage_note'][:120]}...\n")

    if doc_calls and not web_failed:
        print("(Coordinator did not recover via document_analysis fallback.)")
    elif doc_calls:
        print("✓ Coordinator recovered by delegating to document_analysis.\n")

    if not result.final_report:
        print("No final report produced.")
        return

    print("--- Final report (excerpt) ---")
    print(f"Executive summary: {result.final_report['executive_summary'][:200]}...\n")
    print(f"Domain sections: {len(result.final_report['domain_sections'])}")
    print(f"Conflicts: {len(result.final_report['conflicts'])}")
    print(f"Coverage gaps: {len(result.final_report['coverage_gaps'])}")


if __name__ == "__main__":
    main()