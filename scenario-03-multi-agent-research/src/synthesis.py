"""Synthesis agent: turns aggregated findings into a structured report.

Per Task Statement 5.6, the synthesis stage MUST preserve provenance,
annotate conflicts, handle temporal data correctly, and surface coverage
gaps. The output schema enforces all four requirements structurally.

This is the first scenario where we use Claude's tool_use mechanism
purely for structured output — the 'tool' isn't doing anything; it's
just a schema that constrains the model's response shape.
"""
from __future__ import annotations

from dataclasses import dataclass

from .agent_loop import run_agent_loop


# --- The synthesis output schema ---
# This is a tool_use schema, but the "tool" is just a schema container.
# Per Task 4.3 (which we'll exercise more in Scenario 6), tool_use is
# the most reliable way to enforce structured output from Claude.

SYNTHESIS_OUTPUT_SCHEMA = {
    "name": "submit_synthesis_report",
    "description": (
        "Submit the final synthesis report. Must include all findings "
        "organized by domain, all conflicts annotated with sources, "
        "and explicit coverage gaps."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "topic": {
                "type": "string",
                "description": "The original research topic.",
            },
            "executive_summary": {
                "type": "string",
                "description": (
                    "2-4 sentence summary of the most significant findings. "
                    "Do not include claims here that aren't also covered "
                    "in the domain sections below with sources."
                ),
            },
            "domain_sections": {
                "type": "array",
                "description": (
                    "One section per distinct domain investigated. "
                    "Group findings by domain rather than by source."
                ),
                "items": {
                    "type": "object",
                    "properties": {
                        "domain": {
                            "type": "string",
                            "description": "The domain name (e.g., 'music', 'film').",
                        },
                        "key_findings": {
                            "type": "array",
                            "description": "Findings in this domain, each with source.",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "claim": {"type": "string"},
                                    "source_name": {"type": "string"},
                                    "source_url": {"type": "string"},
                                    "publication_date_iso": {
                                        "type": "string",
                                        "description": (
                                            "ISO 8601 date the claim's source "
                                            "was published or data was collected."
                                        ),
                                    },
                                },
                                "required": [
                                    "claim",
                                    "source_name",
                                    "publication_date_iso",
                                ],
                            },
                        },
                    },
                    "required": ["domain", "key_findings"],
                },
            },
            "conflicts": {
                "type": "array",
                "description": (
                    "Findings from different sources that contradict each "
                    "other on the same point. Each conflict preserves both "
                    "claims with their sources. DO NOT arbitrarily pick "
                    "one — annotate both."
                ),
                "items": {
                    "type": "object",
                    "properties": {
                        "topic": {
                            "type": "string",
                            "description": "What the conflict is about.",
                        },
                        "claim_a": {"type": "string"},
                        "source_a": {"type": "string"},
                        "date_a": {"type": "string"},
                        "claim_b": {"type": "string"},
                        "source_b": {"type": "string"},
                        "date_b": {"type": "string"},
                        "resolution_note": {
                            "type": "string",
                            "description": (
                                "If the conflict is explained by different "
                                "dates, sample sizes, or methodologies, "
                                "note that here. Otherwise leave empty."
                            ),
                        },
                    },
                    "required": ["topic", "claim_a", "source_a", "claim_b", "source_b"],
                },
            },
            "coverage_gaps": {
                "type": "array",
                "description": (
                    "Domains or sub-topics that the topic likely covers "
                    "but for which no findings were provided. Surfacing "
                    "gaps lets the coordinator re-delegate targeted "
                    "investigations."
                ),
                "items": {
                    "type": "object",
                    "properties": {
                        "domain": {
                            "type": "string",
                            "description": "The missing domain or sub-topic.",
                        },
                        "rationale": {
                            "type": "string",
                            "description": (
                                "Why this domain is expected to be relevant "
                                "to the topic but was not covered by the "
                                "findings provided."
                            ),
                        },
                    },
                    "required": ["domain", "rationale"],
                },
            },
        },
        "required": [
            "topic",
            "executive_summary",
            "domain_sections",
            "conflicts",
            "coverage_gaps",
        ],
    },
}


# --- Synthesis system prompt ---

SYNTHESIS_SYSTEM_PROMPT = """You are a research synthesis specialist. \
Given a topic and a list of structured findings from research subagents, \
you produce a comprehensive report.

## Your output

You will call the `submit_synthesis_report` tool with your structured \
report. Do NOT write free prose. Every claim in your report must trace \
to a finding in the provided findings list.

## Rules for synthesis

1. **Group by domain, not by source.** If two findings cover music, \
they go in the same domain section, even if from different sources.

2. **Preserve every source.** Every claim in your report must include \
its source_name and publication_date_iso fields, taken directly from \
the input findings. Do NOT paraphrase the source attribution.

3. **Annotate conflicts, never resolve them.** If two findings on the \
same topic disagree, add a `conflicts` entry preserving both claims \
with their sources. Add a `resolution_note` only if the difference is \
explained by different dates, sample sizes, or methodologies — never \
silently pick one as "correct."

4. **Surface coverage gaps explicitly.** Look at the topic and consider \
what domains a thorough investigation would cover. For each domain that \
the topic likely spans but is missing from the findings, add a \
`coverage_gaps` entry. Do NOT skip this — gaps are how the coordinator \
knows to do further investigation.

5. **Do not invent claims.** If you find yourself reasoning beyond what \
the findings support, stop. Synthesis is recombination, not generation."""


# --- Synthesis runner ---

@dataclass
class SynthesisResult:
    """Output of one synthesis run."""
    report: dict | None
    raw_text: str
    iterations: int
    is_error: bool = False
    error_detail: str = ""


def run_synthesis(topic: str, findings: list[dict]) -> SynthesisResult:
    """Run the synthesis agent against a topic and a list of findings.

    Args:
        topic: the original research topic.
        findings: aggregated findings from coordinator's subagent invocations.

    Returns:
        SynthesisResult with the structured report (or error info).
    """
    if not findings:
        return SynthesisResult(
            report=None,
            raw_text="",
            iterations=0,
            is_error=True,
            error_detail="No findings provided; cannot synthesize.",
        )

    # Render findings as the synthesis input prompt
    findings_block = "\n\n".join(
        f"FINDING {i+1}:\n"
        f"  Claim: {f['claim']}\n"
        f"  Source: {f['source_name']} ({f.get('source_url', 'n/a')})\n"
        f"  Date: {f['publication_date_iso']}\n"
        f"  Domain: {f['domain']}"
        for i, f in enumerate(findings)
    )

    user_message = (
        f"TOPIC: {topic}\n\n"
        f"FINDINGS (from research subagents):\n\n{findings_block}\n\n"
        f"Produce the synthesis report by calling submit_synthesis_report."
    )

    # We capture the structured output by intercepting the tool call.
    captured = {}

    def _capture_report(tool_input: dict) -> dict:
        """The 'tool' implementation just captures the report and returns ok."""
        captured["report"] = tool_input
        return {"status": "received"}

    run, _history = run_agent_loop(
        user_message=user_message,
        system_prompt=SYNTHESIS_SYSTEM_PROMPT,
        tool_schemas=[SYNTHESIS_OUTPUT_SCHEMA],
        tool_implementations={"submit_synthesis_report": _capture_report},
    )

    if "report" not in captured:
        return SynthesisResult(
            report=None,
            raw_text=run.final_text,
            iterations=run.iterations,
            is_error=True,
            error_detail="Synthesis agent did not call submit_synthesis_report.",
        )

    return SynthesisResult(
        report=captured["report"],
        raw_text=run.final_text,
        iterations=run.iterations,
    )