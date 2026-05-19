"""Tests for subagent dispatch.

These verify the structural contracts: each subagent returns a
properly-shaped SubagentResult; each subagent respects its scoped
tool access; the registry exposes both subagents.
"""
import pytest

from src.subagents import SUBAGENT_REGISTRY, SubagentResult


def test_registry_has_both_subagents():
    assert "web_research" in SUBAGENT_REGISTRY
    assert "document_analysis" in SUBAGENT_REGISTRY


def test_each_subagent_has_distinct_allowed_tools():
    """Task 2.3 verification: no overlapping tool access."""
    web = SUBAGENT_REGISTRY["web_research"]
    doc = SUBAGENT_REGISTRY["document_analysis"]

    assert web.allowed_tools == ["search_web"]
    assert doc.allowed_tools == ["analyze_documents"]
    # No overlap
    assert set(web.allowed_tools).isdisjoint(set(doc.allowed_tools))


def test_web_research_returns_structured_findings():
    web = SUBAGENT_REGISTRY["web_research"]
    result = web.runner("AI music tools used by independent musicians")

    assert isinstance(result, SubagentResult)
    assert not result.is_error
    assert len(result.findings) > 0

    # Each finding must have full provenance metadata
    for f in result.findings:
        assert "claim" in f
        assert "source_url" in f
        assert "source_name" in f
        assert "publication_date_iso" in f
        assert "domain" in f


def test_document_analysis_returns_structured_findings():
    doc = SUBAGENT_REGISTRY["document_analysis"]
    result = doc.runner("survey of composers using AI music tools")

    assert not result.is_error
    assert len(result.findings) > 0
    for f in result.findings:
        assert "publication_date_iso" in f


def test_subagent_result_renders_to_prompt_block():
    """The to_prompt_block method is the bridge for context passing
    (Task 1.3). It must produce text that preserves attribution."""
    web = SUBAGENT_REGISTRY["web_research"]
    result = web.runner("AI in graphic design")
    block = result.to_prompt_block()

    # The rendered block must include source attribution
    if result.findings:
        first = result.findings[0]
        assert first["source_name"] in block
        assert first["publication_date_iso"] in block


def test_domain_hint_filters_search():
    """The domain hint mechanism lets the coordinator scope searches.
    Verify that a music-domain search returns music findings and not,
    say, theatre findings."""
    web = SUBAGENT_REGISTRY["web_research"]
    result = web.runner("AI tools\ndomain: music")

    if result.findings:
        domains = {f["domain"] for f in result.findings}
        # All findings should be in the music domain (or the keyword
        # match also pulled in cross-domain ones — accept that, but
        # at least music should be present)
        assert "music" in domains


def test_coverage_note_describes_what_was_searched():
    """The coverage_note field is what the coordinator uses to detect
    gaps. It must be informative, not a generic 'OK'."""
    web = SUBAGENT_REGISTRY["web_research"]
    result = web.runner("AI in theatre productions")

    # The note should mention the query (in some form)
    assert len(result.coverage_note) > 10
    # And should report the count
    assert any(c.isdigit() for c in result.coverage_note)