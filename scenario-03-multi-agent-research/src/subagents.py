"""Subagent registry and dispatch.

Per Task Statement 1.3, each subagent type is an AgentDefinition with:
- A descriptive name and description (used for coordinator routing)
- A focused system prompt (per Task 2.3, scoped to the subagent's role)
- An allowed_tools list (per Task 2.3, no cross-specialization tools)
- A dispatch function that runs the subagent's agent loop

Subagents operate with isolated context. They do NOT inherit the
coordinator's conversation history — they only see what the coordinator
explicitly passes in their invocation prompt.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Callable

from . import fake_data


# --- Subagent input/output contracts ---

@dataclass
class SubagentResult:
    """The structured output every subagent returns.

    Per Task 1.3 'Including complete findings from prior agents directly
    in the subagent's prompt' — this structured shape is what the
    coordinator embeds into the synthesis agent's prompt later.

    Per Task 5.6 'requiring publication or data collection dates in
    structured outputs' — every finding includes its date.
    """
    findings: list[dict]      # serialized Finding records
    coverage_note: str        # what was searched, what was found, gaps
    is_error: bool = False
    error_category: str = ""
    error_detail: str = ""

    def to_prompt_block(self) -> str:
        """Render this result for embedding in another agent's prompt."""
        if self.is_error:
            return (
                f"[ERROR from subagent: category={self.error_category}, "
                f"detail={self.error_detail}]"
            )
        lines = []
        for f in self.findings:
            lines.append(
                f"- Claim: {f['claim']}\n"
                f"  Source: {f['source_name']} ({f['source_url']})\n"
                f"  Date: {f['publication_date_iso']}\n"
                f"  Domain: {f['domain']}"
            )
        lines.append(f"\n[Coverage note: {self.coverage_note}]")
        return "\n".join(lines)


# --- AgentDefinition ---

@dataclass
class AgentDefinition:
    """Configuration for one specialist subagent.

    Mirrors the Claude Agent SDK's AgentDefinition shape (Task 1.3).
    In a real SDK setup the SDK would dispatch through this; in our
    teaching scaffold the dispatcher in coordinator.py invokes the
    `runner` callable directly.
    """
    name: str
    description: str
    system_prompt: str
    allowed_tools: list[str]
    runner: Callable[[str], SubagentResult]


# --- Specialist subagents ---

def _run_web_research(prompt: str) -> SubagentResult:
    """Web research subagent.

    Per Task 2.3, this subagent has access ONLY to search_web — not
    document analysis tools, not synthesis tools. Cross-specialization
    misuse is structurally prevented.

    The prompt is parsed for a domain hint (a substring like
    'domain: music' if the coordinator wants to direct the search).
    Production agents would use the model to parse the prompt; we
    keep it deterministic here for testing.
    """
    # Extract a search query and optional domain hint from the prompt
    # Real implementation: a model call. For now: parse pragma-style hints.
    query = prompt
    domain_hint = None
    if "domain:" in prompt.lower():
        # crude extraction; production would use the model
        for line in prompt.split("\n"):
            if line.lower().startswith("domain:"):
                domain_hint = line.split(":", 1)[1].strip()
                break

    findings = fake_data.search_web(query, domain_hint=domain_hint)

    return SubagentResult(
        findings=[_finding_to_dict(f) for f in findings],
        coverage_note=(
            f"Searched for '{query[:60]}...'. "
            f"Found {len(findings)} results"
            + (f" in domain '{domain_hint}'" if domain_hint else "")
            + "."
        ),
    )


def _run_document_analysis(prompt: str) -> SubagentResult:
    """Document analysis subagent.

    Per Task 2.3, access ONLY to analyze_documents. Same scoping
    rationale as web_research.
    """
    query = prompt
    domain_hint = None
    if "domain:" in prompt.lower():
        for line in prompt.split("\n"):
            if line.lower().startswith("domain:"):
                domain_hint = line.split(":", 1)[1].strip()
                break

    findings = fake_data.analyze_documents(query, domain_hint=domain_hint)

    return SubagentResult(
        findings=[_finding_to_dict(f) for f in findings],
        coverage_note=(
            f"Analyzed documents matching '{query[:60]}...'. "
            f"Found {len(findings)} sources"
            + (f" in domain '{domain_hint}'" if domain_hint else "")
            + "."
        ),
    )


def _finding_to_dict(f: fake_data.Finding) -> dict:
    return {
        "claim": f.claim,
        "source_url": f.source_url,
        "source_name": f.source_name,
        "publication_date_iso": f.publication_date_iso,
        "domain": f.domain,
    }


# --- Registry ---

SUBAGENT_REGISTRY: dict[str, AgentDefinition] = {
    "web_research": AgentDefinition(
        name="web_research",
        description=(
            "Searches the web for current information on a topic. Best "
            "for news articles, industry reports, recent events, and "
            "general-audience sources. Provide a focused query and "
            "optional 'domain: <domain_name>' hint to scope the search."
        ),
        system_prompt=(
            "You are a web research specialist. Given a query, you "
            "search the web and return structured findings. Each finding "
            "must include the claim, source URL, source name, and "
            "publication date. Be thorough but stay focused on the "
            "specific query you were given."
        ),
        allowed_tools=["search_web"],
        runner=_run_web_research,
    ),
    "document_analysis": AgentDefinition(
        name="document_analysis",
        description=(
            "Analyzes academic papers, industry reports, and other "
            "longer-form documents on a topic. Best for in-depth "
            "studies, economic analyses, and survey research. Provide "
            "a focused query and optional 'domain: <domain_name>' hint."
        ),
        system_prompt=(
            "You are a document analysis specialist. Given a query, "
            "you analyze longer-form documents and return structured "
            "findings with full source attribution including publication "
            "dates. Prefer primary sources (research papers, official "
            "reports) over secondary commentary."
        ),
        allowed_tools=["analyze_documents"],
        runner=_run_document_analysis,
    ),
}