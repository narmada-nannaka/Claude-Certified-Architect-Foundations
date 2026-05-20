"""Tests for the coverage-gap feedback loop.

The pipeline mocks both the coordinator (which we already trust) and
the synthesis runs so we can control exactly when gaps appear and
when they don't.
"""
from unittest.mock import MagicMock, patch

from src.pipeline import MAX_REFINEMENT_ITERATIONS, run_research_pipeline


def _fake_synthesis_result(report_with_gaps: dict | None, is_error: bool = False):
    """Helper to build a synthesis result with given gaps."""
    r = MagicMock()
    r.is_error = is_error
    r.report = report_with_gaps
    r.error_detail = "test error" if is_error else ""
    r.raw_text = ""
    r.iterations = 1
    return r


def _fake_session(findings_count: int):
    """Helper to build a coordinator session with mocked findings."""
    s = MagicMock()
    s.coordinator_run = MagicMock(iterations=2)
    s.all_findings = [
        {
            "claim": f"finding {i}",
            "source_name": "test source",
            "source_url": "https://x",
            "publication_date_iso": "2024-01-01",
            "domain": "visual_arts",
        }
        for i in range(findings_count)
    ]
    s.subagent_invocations = []
    return s


def test_pipeline_terminates_when_no_gaps_first_round():
    """Happy path: synthesis finds no gaps; pipeline ends after one
    synthesis round."""
    perfect_report = {
        "topic": "test",
        "executive_summary": "all covered",
        "domain_sections": [],
        "conflicts": [],
        "coverage_gaps": [],
    }

    with patch("src.pipeline.run_coordinator") as mock_coord, \
         patch("src.pipeline.run_synthesis") as mock_synth:
        mock_coord.return_value = _fake_session(findings_count=5)
        mock_synth.return_value = _fake_synthesis_result(perfect_report)

        result = run_research_pipeline("test topic")

        assert result.refinement_iterations == 0
        assert not result.hit_iteration_cap
        assert mock_synth.call_count == 1
        assert len(result.gap_history) == 1
        assert result.gap_history[0] == []


def test_pipeline_runs_gap_fill_when_synthesis_reports_gaps():
    """Sample Q7 pattern: initial synthesis reports gaps; pipeline
    dispatches gap-fill investigations; synthesis re-runs."""
    gappy_report = {
        "topic": "AI in creative industries",
        "executive_summary": "x",
        "domain_sections": [{"domain": "visual_arts", "key_findings": []}],
        "conflicts": [],
        "coverage_gaps": [
            {"domain": "music", "rationale": "missing music coverage"},
            {"domain": "film", "rationale": "missing film coverage"},
        ],
    }
    clean_report = {
        "topic": "AI in creative industries",
        "executive_summary": "x",
        "domain_sections": [],
        "conflicts": [],
        "coverage_gaps": [],
    }

    with patch("src.pipeline.run_coordinator") as mock_coord, \
         patch("src.pipeline.run_synthesis") as mock_synth, \
         patch("src.pipeline._task_tool_implementation") as mock_task:
        mock_coord.return_value = _fake_session(findings_count=3)
        # First synthesis: gaps. Second synthesis: clean.
        mock_synth.side_effect = [
            _fake_synthesis_result(gappy_report),
            _fake_synthesis_result(clean_report),
        ]
        # Gap-fill task calls return successful findings
        mock_task.return_value = {
            "subagent": "test",
            "findings_count": 1,
            "findings": [{
                "claim": "gap-fill finding",
                "source_name": "x",
                "source_url": "y",
                "publication_date_iso": "2024-01-01",
                "domain": "music",
            }],
            "coverage_note": "filled",
        }

        result = run_research_pipeline("AI in creative industries")

        # Synthesis ran twice (initial + after gap-fill)
        assert mock_synth.call_count == 2
        # Gap-fill dispatch happened: 2 gaps × 2 subagents each = 4 calls
        assert mock_task.call_count == 4
        # Final result is the clean second synthesis
        assert result.final_report == clean_report
        assert result.refinement_iterations == 1
        assert not result.hit_iteration_cap


def test_pipeline_hits_iteration_cap_when_gaps_persist():
    """Edge case: synthesis keeps surfacing gaps that gap-fill doesn't
    resolve. The cap engages, the report is preserved with gaps."""
    persistent_gaps = {
        "topic": "test",
        "executive_summary": "x",
        "domain_sections": [],
        "conflicts": [],
        "coverage_gaps": [{"domain": "unfindable", "rationale": "data not available"}],
    }

    with patch("src.pipeline.run_coordinator") as mock_coord, \
         patch("src.pipeline.run_synthesis") as mock_synth, \
         patch("src.pipeline._task_tool_implementation") as mock_task:
        mock_coord.return_value = _fake_session(findings_count=1)
        # Every synthesis run reports the same persistent gap
        mock_synth.return_value = _fake_synthesis_result(persistent_gaps)
        # Gap-fill returns no findings (the data isn't available)
        mock_task.return_value = {
            "subagent": "test",
            "findings_count": 0,
            "findings": [],
            "coverage_note": "no results",
        }

        result = run_research_pipeline("test")

        assert result.hit_iteration_cap is True
        assert result.refinement_iterations == MAX_REFINEMENT_ITERATIONS
        # The report is preserved even with gaps — downstream can see them
        assert result.final_report["coverage_gaps"][0]["domain"] == "unfindable"


def test_pipeline_handles_empty_findings():
    """If the coordinator returns no findings, synthesis can't run.
    The pipeline must surface this cleanly, not crash."""
    with patch("src.pipeline.run_coordinator") as mock_coord:
        mock_coord.return_value = _fake_session(findings_count=0)

        result = run_research_pipeline("test")

        assert result.final_report is None
        assert len(result.all_findings) == 0


def test_pipeline_records_gap_history_for_observability():
    """Each round's gaps are recorded so we can audit what was
    fixed across rounds."""
    initial_gaps = {
        "topic": "test",
        "executive_summary": "x",
        "domain_sections": [],
        "conflicts": [],
        "coverage_gaps": [{"domain": "music", "rationale": "x"}],
    }
    no_gaps = {
        "topic": "test",
        "executive_summary": "x",
        "domain_sections": [],
        "conflicts": [],
        "coverage_gaps": [],
    }

    with patch("src.pipeline.run_coordinator") as mock_coord, \
         patch("src.pipeline.run_synthesis") as mock_synth, \
         patch("src.pipeline._task_tool_implementation") as mock_task:
        mock_coord.return_value = _fake_session(findings_count=1)
        mock_synth.side_effect = [
            _fake_synthesis_result(initial_gaps),
            _fake_synthesis_result(no_gaps),
        ]
        mock_task.return_value = {"findings": [], "findings_count": 0}

        result = run_research_pipeline("test")

        # Two synthesis rounds: gaps then no gaps
        assert len(result.gap_history) == 2
        assert len(result.gap_history[0]) == 1
        assert len(result.gap_history[1]) == 0


def test_gap_fill_invocations_have_phase_marker():
    """Observability: gap-fill invocations are distinguished from
    initial coordinator invocations via the 'phase' field."""
    gappy_report = {
        "topic": "test",
        "executive_summary": "x",
        "domain_sections": [],
        "conflicts": [],
        "coverage_gaps": [{"domain": "music", "rationale": "x"}],
    }
    clean_report = {
        "topic": "test",
        "executive_summary": "x",
        "domain_sections": [],
        "conflicts": [],
        "coverage_gaps": [],
    }

    with patch("src.pipeline.run_coordinator") as mock_coord, \
         patch("src.pipeline.run_synthesis") as mock_synth, \
         patch("src.pipeline._task_tool_implementation") as mock_task:
        mock_coord.return_value = _fake_session(findings_count=1)
        mock_synth.side_effect = [
            _fake_synthesis_result(gappy_report),
            _fake_synthesis_result(clean_report),
        ]
        mock_task.return_value = {"findings": [], "findings_count": 0}

        result = run_research_pipeline("test")

        # Find gap-fill invocations
        gap_fill_invs = [i for i in result.all_invocations if i.get("phase") == "gap_fill"]
        assert len(gap_fill_invs) > 0
        # Each should target a specific gap domain
        for inv in gap_fill_invs:
            assert inv["gap_target"] == "music"