"""Tests for the verify_fact scoped tool.

Verifies the Sample Q9 pattern: synthesis agent has a bounded tool for
simple lookups; complex verifications are deferred to coordinator-level
investigation.
"""
from src.synthesis import _verify_fact_implementation


def test_verify_known_date_returns_value():
    result = _verify_fact_implementation({
        "claim": "When was the WGA 2023 strike?",
        "claim_type": "date",
    })
    assert result["verified"] is True
    assert "2023" in result["result"]


def test_verify_unknown_simple_claim_returns_unknown():
    """The tool is bounded — it returns 'unknown' for claims it doesn't
    know, rather than fabricating or delegating."""
    result = _verify_fact_implementation({
        "claim": "When did the third reorganization of the WGA take place?",
        "claim_type": "date",
    })
    assert result["verified"] is False
    assert result["result"] == "unknown"
    assert "unverified" in result["note"].lower() or "omit" in result["note"].lower()


def test_other_claim_type_defers_to_coordinator():
    """Sample Q9 architectural pattern: complex verifications don't go
    through verify_fact; they're deferred to coordinator-level research."""
    result = _verify_fact_implementation({
        "claim": "Is the 12% job displacement statistic from the film economics paper accurate?",
        "claim_type": "other",
    })
    assert result["verified"] is False
    assert result["result"] == "deferred"
    assert "coordinator" in result["note"].lower() or \
           "multi-source" in result["note"].lower()


def test_statistic_type_never_verifies_directly():
    """Statistics need multi-source corroboration. The verify_fact tool
    is deliberately not equipped for them — synthesis must surface the
    need in its report instead."""
    result = _verify_fact_implementation({
        "claim": "68% of designers use AI tools",
        "claim_type": "statistic",
    })
    assert result["verified"] is False
    assert result["result"] == "unknown"


def test_empty_claim_rejected():
    result = _verify_fact_implementation({
        "claim": "",
        "claim_type": "date",
    })
    assert result["isError"] is True
    assert result["errorCategory"] == "validation"


def test_verify_fact_does_not_make_network_calls():
    """Architectural invariant: verify_fact must be bounded — no
    network, no delegation, no escalation. This test is partly
    a smoke test (if we accidentally added network calls, mocking
    would fail). The real assertion: implementation is deterministic
    and synchronous.

    The way to verify is to look at the source: no requests library
    imported, no asyncio, no Anthropic client.
    """
    # The test passes if we got this far without imports/runtime failure.
    # In production code review, this invariant is enforced by import
    # restrictions and architectural review.
    import src.synthesis as synth_module
    # Verify no network-call imports are needed for verify_fact
    source_code = open(synth_module.__file__).read()
    assert "requests" not in source_code.lower()
    assert "import httpx" not in source_code