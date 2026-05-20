"""Tests for synthesis output structure.

These tests focus on schema enforcement and edge cases that the exam
tests around: empty findings, conflicting findings, temporal handling,
coverage gaps. They mock the API to keep tests fast and deterministic.
"""
from unittest.mock import MagicMock, patch

from src.synthesis import (
    SYNTHESIS_OUTPUT_SCHEMA,
    SynthesisResult,
    run_synthesis,
)


def _mock_response(stop_reason, content):
    r = MagicMock()
    r.stop_reason = stop_reason
    r.content = content
    return r


def _tool_use_block(tool_id, name, input_data):
    b = MagicMock()
    b.type = "tool_use"
    b.id = tool_id
    b.name = name
    b.input = input_data
    return b


def _text_block(text):
    b = MagicMock()
    b.type = "text"
    b.text = text
    return b


# --- Schema structure tests ---

def test_schema_requires_all_provenance_fields():
    """Every key_finding must include source_name and date.
    Task 5.6: provenance preservation through synthesis."""
    schema = SYNTHESIS_OUTPUT_SCHEMA["input_schema"]
    key_finding_props = schema["properties"]["domain_sections"]["items"]["properties"]["key_findings"]["items"]
    assert "claim" in key_finding_props["required"]
    assert "source_name" in key_finding_props["required"]
    assert "publication_date_iso" in key_finding_props["required"]


def test_schema_requires_coverage_gaps_field():
    """coverage_gaps must always be present (even if empty).
    Task 5.6: 'coverage annotations indicating which findings are
    well-supported versus which topic areas have gaps.'"""
    schema = SYNTHESIS_OUTPUT_SCHEMA["input_schema"]
    assert "coverage_gaps" in schema["required"]


def test_schema_conflict_structure_preserves_both_sources():
    """A conflict entry must contain claim+source for both sides.
    Task 5.6: 'annotating conflicts with source attribution rather
    than arbitrarily selecting one value.'"""
    schema = SYNTHESIS_OUTPUT_SCHEMA["input_schema"]
    conflict_props = schema["properties"]["conflicts"]["items"]["properties"]
    required = schema["properties"]["conflicts"]["items"]["required"]
    assert "claim_a" in required
    assert "claim_b" in required
    assert "source_a" in required
    assert "source_b" in required


# --- Edge case tests ---

def test_synthesis_with_no_findings_returns_error():
    """Without findings there's nothing to synthesize."""
    result = run_synthesis("test topic", [])
    assert result.is_error is True
    assert "no findings" in result.error_detail.lower()


def test_synthesis_captures_structured_report():
    """End-to-end: synthesis agent calls submit_synthesis_report
    and the runner captures its arguments."""
    findings = [{
        "claim": "AI is used in music production.",
        "source_name": "Music Production Journal",
        "source_url": "https://example.com/x",
        "publication_date_iso": "2024-04-10",
        "domain": "music",
    }]

    fake_report = {
        "topic": "AI in music",
        "executive_summary": "AI is being adopted in music production.",
        "domain_sections": [{
            "domain": "music",
            "key_findings": [{
                "claim": "AI is used in music production.",
                "source_name": "Music Production Journal",
                "source_url": "https://example.com/x",
                "publication_date_iso": "2024-04-10",
            }],
        }],
        "conflicts": [],
        "coverage_gaps": [],
    }

    with patch("src.agent_loop.Anthropic") as MockAnthropic:
        client = MockAnthropic.return_value
        client.messages.create.side_effect = [
            _mock_response(
                "tool_use",
                [_tool_use_block("t1", "submit_synthesis_report", fake_report)],
            ),
            _mock_response("end_turn", [_text_block("done")]),
        ]

        result = run_synthesis("AI in music", findings)

        assert not result.is_error
        assert result.report["topic"] == "AI in music"
        assert len(result.report["domain_sections"]) == 1
        assert result.report["domain_sections"][0]["domain"] == "music"


def test_synthesis_reports_error_if_tool_never_called():
    """If the synthesis agent produces text without calling the tool,
    that's a structural failure we surface as an error."""
    with patch("src.agent_loop.Anthropic") as MockAnthropic:
        client = MockAnthropic.return_value
        client.messages.create.return_value = _mock_response(
            "end_turn",
            [_text_block("Here is my report in prose form: ...")],
        )

        result = run_synthesis("test", [{
            "claim": "x",
            "source_name": "y",
            "publication_date_iso": "2024-01-01",
            "domain": "test",
        }])

        assert result.is_error is True
        assert "did not call" in result.error_detail.lower()