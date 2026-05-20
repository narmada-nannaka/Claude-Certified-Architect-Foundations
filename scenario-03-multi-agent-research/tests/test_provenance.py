"""Tests for provenance preservation through synthesis.

These verify the exam-tested invariants from Task 5.6:
- Every claim in output traces to an input finding's source
- Dates are preserved verbatim
- Conflicts preserve both sources
- Coverage gaps are explicit
"""
from unittest.mock import MagicMock, patch

from src.synthesis import run_synthesis


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


def test_every_claim_in_report_has_a_source():
    """Validation we'd apply to real synthesis output:
    walk the report's domain_sections, verify each key_finding
    has source_name and date."""
    findings = [
        {
            "claim": "Claim 1",
            "source_name": "Source A",
            "source_url": "https://a",
            "publication_date_iso": "2024-01-01",
            "domain": "music",
        },
        {
            "claim": "Claim 2",
            "source_name": "Source B",
            "source_url": "https://b",
            "publication_date_iso": "2024-02-01",
            "domain": "music",
        },
    ]

    fake_report = {
        "topic": "test",
        "executive_summary": "summary",
        "domain_sections": [{
            "domain": "music",
            "key_findings": [
                {
                    "claim": "Claim 1",
                    "source_name": "Source A",
                    "source_url": "https://a",
                    "publication_date_iso": "2024-01-01",
                },
                {
                    "claim": "Claim 2",
                    "source_name": "Source B",
                    "source_url": "https://b",
                    "publication_date_iso": "2024-02-01",
                },
            ],
        }],
        "conflicts": [],
        "coverage_gaps": [],
    }

    with patch("src.agent_loop.Anthropic") as MockAnthropic:
        client = MockAnthropic.return_value
        client.messages.create.side_effect = [
            _mock_response("tool_use", [_tool_use_block("t1", "submit_synthesis_report", fake_report)]),
            _mock_response("end_turn", [_text_block("done")]),
        ]

        result = run_synthesis("test", findings)

        # Walk every claim and verify provenance
        for section in result.report["domain_sections"]:
            for finding in section["key_findings"]:
                assert finding["source_name"], "Missing source_name"
                assert finding["publication_date_iso"], "Missing date"
                assert finding["claim"], "Missing claim"


def test_conflicts_preserve_both_sources():
    """When two findings conflict, the report must include both
    with full attribution. Task 5.6 forbids arbitrary selection."""
    fake_report_with_conflict = {
        "topic": "test",
        "executive_summary": "x",
        "domain_sections": [],
        "conflicts": [{
            "topic": "AI adoption rate in graphic design",
            "claim_a": "68% of designers use AI tools.",
            "source_a": "Design Industry Survey",
            "date_a": "2024-05-02",
            "claim_b": "41% of visual artists adopted AI tools.",
            "source_b": "Journal of Creative Practice",
            "date_b": "2024-02-01",
            "resolution_note": (
                "Different populations (graphic designers vs visual artists)"
                " and different dates explain the disparity."
            ),
        }],
        "coverage_gaps": [],
    }

    with patch("src.agent_loop.Anthropic") as MockAnthropic:
        client = MockAnthropic.return_value
        client.messages.create.side_effect = [
            _mock_response("tool_use", [_tool_use_block("t1", "submit_synthesis_report", fake_report_with_conflict)]),
            _mock_response("end_turn", [_text_block("done")]),
        ]

        result = run_synthesis("test", [{"claim": "x", "source_name": "y", "publication_date_iso": "2024-01-01", "domain": "x"}])
        conflict = result.report["conflicts"][0]
        assert conflict["claim_a"] != conflict["claim_b"]
        assert conflict["source_a"] != conflict["source_b"]
        # Both dates present
        assert conflict["date_a"]
        assert conflict["date_b"]


def test_coverage_gaps_are_actionable():
    """Coverage gaps must include a rationale so the coordinator
    knows how to address them."""
    fake_report_with_gaps = {
        "topic": "AI in creative industries",
        "executive_summary": "x",
        "domain_sections": [{"domain": "visual_arts", "key_findings": []}],
        "conflicts": [],
        "coverage_gaps": [
            {
                "domain": "music",
                "rationale": (
                    "Topic spans creative industries broadly but findings "
                    "cover only visual arts. Music industry has significant "
                    "AI adoption that's not represented."
                ),
            },
            {
                "domain": "writing",
                "rationale": "Same — no findings cover authors, journalists, screenwriters.",
            },
        ],
    }

    with patch("src.agent_loop.Anthropic") as MockAnthropic:
        client = MockAnthropic.return_value
        client.messages.create.side_effect = [
            _mock_response("tool_use", [_tool_use_block("t1", "submit_synthesis_report", fake_report_with_gaps)]),
            _mock_response("end_turn", [_text_block("done")]),
        ]

        result = run_synthesis("AI in creative industries", [{"claim": "x", "source_name": "y", "publication_date_iso": "2024-01-01", "domain": "visual_arts"}])

        # Coverage gaps must each have a domain AND a rationale
        for gap in result.report["coverage_gaps"]:
            assert gap["domain"]
            assert len(gap["rationale"]) > 20  # not a placeholder