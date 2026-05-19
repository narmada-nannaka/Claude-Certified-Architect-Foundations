"""Mock research data for offline testing.

Realistic-shaped findings across multiple creative-industry domains
so we can exercise:
- Task 1.2's risk: 'overly narrow task decomposition leading to
  incomplete coverage of broad research topics' (Sample Question 7)
- Task 5.6: provenance preservation through synthesis

The data is deliberately spread across many sub-domains so that a
coordinator with weak decomposition will visibly miss some.
"""
from dataclasses import dataclass
from typing import Literal


@dataclass
class Finding:
    """A single research finding with full provenance metadata.

    Per Task 5.6, claim-source mappings must travel through synthesis
    intact. Every finding is a structured record, not free prose.
    """
    claim: str
    source_url: str
    source_name: str
    publication_date_iso: str
    domain: Literal[
        "visual_arts",
        "music",
        "writing",
        "film",
        "graphic_design",
        "photography",
        "theatre",
    ]


# Web search results, indexed by domain. The web_research subagent
# returns findings filtered by query content.
WEB_FINDINGS: list[Finding] = [
    Finding(
        claim="AI image generators are being integrated into Adobe Photoshop and Procreate workflows by professional illustrators.",
        source_url="https://example.com/news/ai-illustration-2024",
        source_name="ArtsTech Weekly",
        publication_date_iso="2024-03-15",
        domain="visual_arts",
    ),
    Finding(
        claim="68% of surveyed graphic designers report using generative AI for client mood boards in 2024.",
        source_url="https://example.com/survey/design-2024",
        source_name="Design Industry Survey",
        publication_date_iso="2024-05-02",
        domain="graphic_design",
    ),
    Finding(
        claim="Adobe Stock now accepts AI-generated images with mandatory provenance disclosure.",
        source_url="https://example.com/news/adobe-stock-policy",
        source_name="Photo Industry News",
        publication_date_iso="2024-02-20",
        domain="photography",
    ),
    Finding(
        claim="Independent musicians use Suno and Udio to prototype song arrangements before working with producers.",
        source_url="https://example.com/music/ai-tools-2024",
        source_name="Music Production Journal",
        publication_date_iso="2024-04-10",
        domain="music",
    ),
    Finding(
        claim="Major record labels have filed lawsuits against AI music generation companies over training data.",
        source_url="https://example.com/legal/music-ai-suits",
        source_name="Entertainment Law Today",
        publication_date_iso="2024-06-05",
        domain="music",
    ),
    Finding(
        claim="Novelists report using LLMs for brainstorming and editing but resist using them for full draft generation.",
        source_url="https://example.com/writers/survey-2024",
        source_name="Authors Guild Quarterly",
        publication_date_iso="2024-01-30",
        domain="writing",
    ),
    Finding(
        claim="The Writers Guild's 2023 strike resulted in contract terms restricting AI use in screenwriting.",
        source_url="https://example.com/wga/2023-contract",
        source_name="Variety",
        publication_date_iso="2023-09-27",
        domain="writing",
    ),
    Finding(
        claim="VFX studios use AI for rotoscoping and background generation, reducing time per shot by 30-40%.",
        source_url="https://example.com/vfx/ai-pipeline-2024",
        source_name="Film Technology Review",
        publication_date_iso="2024-03-22",
        domain="film",
    ),
    Finding(
        claim="Theatre productions remain largely untouched by generative AI; live performance economics favor human labor.",
        source_url="https://example.com/theatre/ai-impact-2024",
        source_name="Stage & Screen",
        publication_date_iso="2024-04-15",
        domain="theatre",
    ),
]


# Document analysis findings — typically deeper, paper-style citations
DOCUMENT_FINDINGS: list[Finding] = [
    Finding(
        claim="Study of 200 visual artists shows 41% have adopted AI tools, primarily for early-stage ideation.",
        source_url="https://example.com/paper/artists-study-2024.pdf",
        source_name="Journal of Creative Practice, Vol 12",
        publication_date_iso="2024-02-01",
        domain="visual_arts",
    ),
    Finding(
        claim="Economic analysis of the film industry suggests AI VFX may displace 12% of mid-tier compositing jobs by 2027.",
        source_url="https://example.com/paper/film-economics-2024.pdf",
        source_name="Media Economics Quarterly",
        publication_date_iso="2024-05-10",
        domain="film",
    ),
    Finding(
        claim="Survey of 80 working composers: 55% use AI for stem separation; 12% for melody generation.",
        source_url="https://example.com/paper/composer-survey.pdf",
        source_name="Composers Forum Research",
        publication_date_iso="2024-03-01",
        domain="music",
    ),
    Finding(
        claim="Legal review of WGA-AMPTP contract: AI cannot be credited as writer; AI-generated material does not establish authorship for residuals.",
        source_url="https://example.com/paper/wga-legal-analysis.pdf",
        source_name="Hollywood Reporter Legal",
        publication_date_iso="2023-10-15",
        domain="writing",
    ),
]


def search_web(query: str, domain_hint: str | None = None) -> list[Finding]:
    """Mock web search. Returns findings whose claim matches query terms.

    Real implementation would call a search API; we filter our fixture
    so the test surface stays deterministic.
    """
    query_lower = query.lower()
    results = []
    for f in WEB_FINDINGS:
        # Match if query terms appear in claim, or domain hint matches.
        claim_lower = f.claim.lower()
        if any(term in claim_lower for term in query_lower.split()):
            results.append(f)
        elif domain_hint and f.domain == domain_hint:
            results.append(f)
    return results[:5]  # Cap at 5 to simulate API page size


def analyze_documents(query: str, domain_hint: str | None = None) -> list[Finding]:
    """Mock document analysis. Same matching pattern as search_web."""
    query_lower = query.lower()
    results = []
    for f in DOCUMENT_FINDINGS:
        claim_lower = f.claim.lower()
        if any(term in claim_lower for term in query_lower.split()):
            results.append(f)
        elif domain_hint and f.domain == domain_hint:
            results.append(f)
    return results[:3]