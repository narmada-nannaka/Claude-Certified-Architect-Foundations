"""End-to-end research pipeline with coverage-gap feedback loop.

Implements Task Statement 1.2's iterative refinement pattern:
1. Coordinator runs initial investigation.
2. Synthesis produces structured report with coverage_gaps.
3. If gaps exist AND we haven't exceeded the iteration cap,
   coordinator re-delegates targeted investigations.
4. Synthesis re-runs with the expanded findings.
5. Repeat until either no gaps remain or cap is hit.

The cap is a convergence safety net — not the primary stopping
mechanism, per Task 1.1's anti-pattern list.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .coordinator import run_coordinator, _task_tool_implementation
from .synthesis import run_synthesis


MAX_REFINEMENT_ITERATIONS = 3  # cap on the gap-fill loop


@dataclass
class PipelineResult:
    """Complete pipeline output across all refinement iterations."""
    topic: str
    refinement_iterations: int = 0
    final_report: dict | None = None
    all_findings: list[dict] = field(default_factory=list)
    all_invocations: list[dict] = field(default_factory=list)
    gap_history: list[list[dict]] = field(default_factory=list)  # gaps per iteration
    hit_iteration_cap: bool = False


def run_research_pipeline(topic: str) -> PipelineResult:
    """Run coordinator + synthesis with iterative gap-fill refinement.

    Strategy:
    1. Initial coordinator run produces findings.
    2. Synthesis surfaces gaps.
    3. While gaps exist and we have budget:
       - Spawn targeted subagent invocations for each gap.
       - Re-run synthesis with expanded findings.
    4. Return the final report.
    """
    result = PipelineResult(topic=topic)

    # Stage 1: initial investigation
    session = run_coordinator(topic)
    result.all_findings.extend(session.all_findings)
    result.all_invocations.extend(session.subagent_invocations)

    if not result.all_findings:
        return result  # nothing to synthesize

    # Stage 2: synthesis + iterative gap-fill loop
    for refinement_round in range(MAX_REFINEMENT_ITERATIONS + 1):
        synth = run_synthesis(topic, result.all_findings)

        if synth.is_error:
            # Synthesis itself failed — surface the error and stop.
            result.final_report = None
            return result

        result.final_report = synth.report
        gaps = synth.report.get("coverage_gaps", [])
        result.gap_history.append(gaps)

        # Termination condition: no gaps OR we've hit the cap.
        if not gaps:
            result.refinement_iterations = refinement_round
            return result

        if refinement_round >= MAX_REFINEMENT_ITERATIONS:
            # Cap reached. Keep the current report (with gaps still in it).
            result.refinement_iterations = refinement_round
            result.hit_iteration_cap = True
            return result

        # Otherwise: dispatch targeted follow-up investigations.
        _dispatch_gap_fill_investigations(gaps, result)

    return result


def _dispatch_gap_fill_investigations(gaps: list[dict], result: PipelineResult) -> None:
    """For each gap, spawn a targeted subagent invocation.

    We dispatch directly to the Task tool implementation rather than
    going through the coordinator's loop. Why: the coordinator's job
    was decomposing the topic; the gaps are already concrete subtopics
    that don't need a second decomposition pass. Direct dispatch is
    faster and more focused.

    Per Task 1.2: 're-delegates to search and analysis subagents with
    TARGETED queries.' The query for each follow-up is the gap's
    domain + rationale, packaged as a focused prompt.
    """
    for gap in gaps:
        domain = gap["domain"]
        rationale = gap.get("rationale", "")

        # Two follow-up invocations per gap: web research and
        # document analysis. This is heavier than strictly needed
        # but ensures both source types are checked.
        web_prompt = (
            f"Find current information on the topic of '{result.topic}' "
            f"as it relates to the {domain} domain.\n"
            f"domain: {domain}\n"
            f"Context: {rationale}"
        )
        web_result = _task_tool_implementation({
            "agent_name": "web_research",
            "prompt": web_prompt,
        })
        result.all_invocations.append({
            "agent_name": "web_research",
            "prompt": web_prompt,
            "result": web_result,
            "phase": "gap_fill",
            "gap_target": domain,
        })
        if not web_result.get("isError"):
            result.all_findings.extend(web_result.get("findings", []))

        doc_prompt = (
            f"Find studies, papers, or reports on '{result.topic}' "
            f"specifically covering the {domain} domain.\n"
            f"domain: {domain}\n"
            f"Context: {rationale}"
        )
        doc_result = _task_tool_implementation({
            "agent_name": "document_analysis",
            "prompt": doc_prompt,
        })
        result.all_invocations.append({
            "agent_name": "document_analysis",
            "prompt": doc_prompt,
            "result": doc_result,
            "phase": "gap_fill",
            "gap_target": domain,
        })
        if not doc_result.get("isError"):
            result.all_findings.extend(doc_result.get("findings", []))