"""Tests for the Task tool's dispatch logic.

These verify the Task tool correctly routes to subagents in the
registry, handles unknown subagent names, and records invocations
in the session.
"""
from src.coordinator import (
    _task_tool_implementation,
    ResearchSession,
    run_coordinator,
)


def test_task_dispatch_routes_to_web_research():
    result = _task_tool_implementation({
        "agent_name": "web_research",
        "prompt": "AI tools used by independent musicians",
    })

    assert not result.get("isError")
    assert result["subagent"] == "web_research"
    assert result["findings_count"] > 0
    assert len(result["findings"]) == result["findings_count"]


def test_task_dispatch_routes_to_document_analysis():
    result = _task_tool_implementation({
        "agent_name": "document_analysis",
        "prompt": "survey of composers using AI",
    })

    assert not result.get("isError")
    assert result["subagent"] == "document_analysis"


def test_task_dispatch_rejects_unknown_subagent():
    """The schema enum SHOULD prevent this, but the dispatch must
    also defend against it in case the schema is bypassed."""
    result = _task_tool_implementation({
        "agent_name": "literature_review",  # not in registry
        "prompt": "x",
    })

    assert result["isError"] is True
    assert result["errorCategory"] == "validation"
    assert "available_agents" in result


def test_task_dispatch_rejects_empty_prompt():
    """A subagent with no context can't do useful work. Reject early."""
    result = _task_tool_implementation({
        "agent_name": "web_research",
        "prompt": "",
    })

    assert result["isError"] is True


def test_research_session_records_invocations():
    """The session must accumulate all subagent invocations and findings
    for observability and downstream synthesis."""
    session = ResearchSession(topic="test topic")

    fake_result = {
        "subagent": "web_research",
        "findings_count": 2,
        "findings": [
            {"claim": "A", "source_url": "x", "source_name": "y", "publication_date_iso": "2024-01-01", "domain": "music"},
            {"claim": "B", "source_url": "x", "source_name": "y", "publication_date_iso": "2024-02-01", "domain": "film"},
        ],
        "coverage_note": "found 2",
    }
    session.add_invocation("web_research", "test prompt", fake_result)

    assert len(session.subagent_invocations) == 1
    assert len(session.all_findings) == 2


def test_research_session_does_not_record_error_findings():
    """When a subagent invocation errors, its (nonexistent) findings
    must not pollute the aggregated findings list."""
    session = ResearchSession(topic="test")
    error_result = {
        "isError": True,
        "errorCategory": "transient",
        "subagent": "web_research",
    }
    session.add_invocation("web_research", "x", error_result)

    assert len(session.subagent_invocations) == 1
    assert len(session.all_findings) == 0