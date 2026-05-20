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


# --- The verify_fact scoped tool ---
# Per Task 2.3 / Sample Question 9: a scoped cross-role tool for
# the synthesis agent's high-frequency simple verifications.
# Complex verifications still route through the coordinator.

VERIFY_FACT_TOOL_SCHEMA = {
    "name": "verify_fact",
    "description": (
        "Verify a simple factual claim against a known fact database. "
        "Use this ONLY for simple lookups: dates, names, basic statistics, "
        "definitions. For complex verifications requiring multi-source "
        "research, do NOT use this tool — instead, note the verification "
        "need in your report's executive_summary so the coordinator can "
        "delegate further research."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "claim": {
                "type": "string",
                "description": "The specific claim to verify, stated precisely.",
            },
            "claim_type": {
                "type": "string",
                "enum": ["date", "name", "statistic", "definition", "other"],
                "description": (
                    "What kind of fact this is. Use 'other' for cases that "
                    "don't fit the categories — but consider whether 'other' "
                    "really means this should be a coordinator-delegated "
                    "verification instead."
                ),
            },
        },
        "required": ["claim", "claim_type"],
    },
}

def _verify_fact_implementation(tool_input: dict) -> dict:
    """Mock implementation of verify_fact.

    In production this would query a fact database, knowledge graph,
    or specialized verification service. For teaching purposes we
    return deterministic responses based on the claim_type.

    Crucially, this tool is FAST and BOUNDED — it never makes a web
    request, never delegates further, never escalates. If it doesn't
    have the answer, it returns 'unknown' and the synthesis agent
    must surface that in its report.
    """
    claim = tool_input.get("claim", "")
    claim_type = tool_input.get("claim_type", "other")

    if not claim:
        return {
            "isError": True,
            "errorCategory": "validation",
            "isRetryable": False,
            "message": "verify_fact requires a non-empty claim.",
        }

    # For 'other' type claims, prompt the synthesis agent to reconsider
    # whether this really should be a coordinator-routed verification
    if claim_type == "other":
        return {
            "verified": False,
            "result": "deferred",
            "note": (
                "This claim doesn't fit a simple verification category. "
                "Consider whether it requires multi-source research "
                "(coordinator-delegated) rather than a simple lookup."
            ),
        }

    # Mock lookup by claim_type. Real implementation would query a DB.
    # Our mock returns 'unknown' for most claims and a few hardcoded
    # known facts so tests can exercise both paths.
    known_facts = {
        "date": {
            "wga 2023 strike": "May 2 to September 27, 2023",
        },
        "name": {
            "wga": "Writers Guild of America",
        },
        "statistic": {},  # all statistics need coordinator-level verification
        "definition": {
            "vfx": "Visual Effects",
        },
    }

    claim_lower = claim.lower()
    for key, value in known_facts.get(claim_type, {}).items():
        if key in claim_lower:
            return {
                "verified": True,
                "result": value,
                "claim_type": claim_type,
            }

    return {
        "verified": False,
        "result": "unknown",
        "note": (
            "This claim could not be verified against the known fact "
            "database. The synthesis agent should either omit the claim "
            "or flag it as unverified in its report."
        ),
    }

# --- Synthesis system prompt ---

SYNTHESIS_SYSTEM_PROMPT = """You are a research synthesis specialist. \
Given a topic and a list of structured findings from research subagents, \
you produce a comprehensive report.

## Available tools

You have two tools:
- `submit_synthesis_report` — call this with your structured report when synthesis is complete.
- `verify_fact` — call this for simple fact-checks during synthesis (dates, names, basic definitions). Use it sparingly and ONLY for simple lookups — for complex verifications, surface the need in your report instead.

## When to use verify_fact

Use it when you're combining findings and need to quickly confirm a simple fact: a date, an organization's full name, a basic definition. The tool is bounded and fast — it returns 'unknown' if it doesn't know, and you should handle that gracefully (omit the claim or flag it as unverified).

Do NOT use verify_fact for:
- Statistics that need multi-source corroboration — those need coordinator-level investigation.
- Complex factual disputes between sources — annotate those as `conflicts` in your report.
- Claims that span multiple domains or require interpretation — surface those in your report's executive_summary.

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
    
    tool_implementations = {
        "submit_synthesis_report": _capture_report,
        "verify_fact": _verify_fact_implementation,
    }
    tool_schemas = [SYNTHESIS_OUTPUT_SCHEMA, VERIFY_FACT_TOOL_SCHEMA]

    run, _history = run_agent_loop(
        user_message=user_message,
        system_prompt=SYNTHESIS_SYSTEM_PROMPT,
        tool_schemas=tool_schemas,
        tool_implementations=tool_implementations,
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
