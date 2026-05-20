"""Tests for structured error propagation from subagents.

Verifies the exam-tested invariants of Task 5.3:
- Error category and retryability are surfaced
- Attempted query is preserved
- Coverage note (containing alternatives) is preserved
- Coordinator's session correctly records the failure
"""
from src import subagents
from src.coordinator import _task_tool_implementation, ResearchSession


def test_simulated_timeout_returns_structured_error():
    """A subagent timeout must produce a structured error with all
    the fields Task 5.3 requires."""
    subagents.SIMULATED_FAILURES["web_research"] = "timeout"
    try:
        result = _task_tool_implementation({
            "agent_name": "web_research",
            "prompt": "AI music tools used by independent musicians",
        })

        assert result["isError"] is True
        assert result["errorCategory"] == "transient"
        assert result["isRetryable"] is True
        assert result["subagent"] == "web_research"
        assert "AI music tools" in result["attempted_prompt"]
        # The coverage_note must contain alternatives the coordinator
        # can pivot to
        assert "alternative" in result["coverage_note"].lower() or \
               "fallback" in result["coverage_note"].lower()
    finally:
        subagents.SIMULATED_FAILURES.clear()


def test_simulated_rate_limit_marks_retryable_with_suggested_delay():
    """Rate limits are transient and the coverage_note should hint
    at the retry delay."""
    subagents.SIMULATED_FAILURES["document_analysis"] = "rate_limit"
    try:
        result = _task_tool_implementation({
            "agent_name": "document_analysis",
            "prompt": "surveys of working composers",
        })

        assert result["isError"] is True
        assert result["isRetryable"] is True
        assert "60" in result["coverage_note"]  # the suggested delay
    finally:
        subagents.SIMULATED_FAILURES.clear()


def test_error_result_not_added_to_session_findings():
    """When a subagent fails, its (empty) findings must not pollute
    the aggregated findings — but the failure IS recorded in invocations."""
    session = ResearchSession(topic="test")
    subagents.SIMULATED_FAILURES["web_research"] = "timeout"
    try:
        result = _task_tool_implementation({
            "agent_name": "web_research",
            "prompt": "test query",
        })
        session.add_invocation("web_research", "test query", result)

        # Invocation recorded for observability
        assert len(session.subagent_invocations) == 1
        assert session.subagent_invocations[0]["result"]["isError"] is True
        # But findings list is empty — errors don't add findings
        assert len(session.all_findings) == 0
    finally:
        subagents.SIMULATED_FAILURES.clear()


def test_structured_error_distinguishes_from_valid_empty_results():
    """A subagent that searches and finds nothing is DIFFERENT from
    a subagent that failed. Both have zero findings, but they have
    different shapes. Per Task 2.2 / Task 5.3."""
    # First: a successful search that found nothing (impossible query)
    result_empty_success = _task_tool_implementation({
        "agent_name": "web_research",
        "prompt": "xyzzy plugh frobnicate",  # no matches in fixture
    })
    # Then: a simulated failure
    subagents.SIMULATED_FAILURES["web_research"] = "timeout"
    try:
        result_error = _task_tool_implementation({
            "agent_name": "web_research",
            "prompt": "anything",
        })
    finally:
        subagents.SIMULATED_FAILURES.clear()

    # The successful-but-empty result has no error flag
    assert "isError" not in result_empty_success or not result_empty_success.get("isError")
    # The error result is clearly marked
    assert result_error["isError"] is True
    # Both have zero findings — that's why we need the flag to distinguish
    assert result_empty_success.get("findings_count", 0) == 0
    assert "findings_count" not in result_error or result_error.get("findings_count", 0) == 0


def test_unknown_subagent_returns_validation_error_not_transient():
    """Calling a nonexistent subagent isn't a transient failure
    that retrying will fix — it's a validation error."""
    result = _task_tool_implementation({
        "agent_name": "literature_review",  # not in registry
        "prompt": "test",
    })

    assert result["isError"] is True
    assert result["errorCategory"] == "validation"
    assert result["isRetryable"] is False  # retrying won't help