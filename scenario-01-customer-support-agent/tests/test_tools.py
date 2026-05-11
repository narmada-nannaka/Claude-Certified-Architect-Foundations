"""Unit-level tests for the MCP tool implementations.

We import the tool functions directly rather than going through the MCP
transport, which keeps tests fast and focused on behavior.
"""
import pytest

from src.mcp_server import (
    get_customer,
    lookup_order,
    process_refund,
    escalate_to_human,
)


def test_get_customer_single_match():
    result = get_customer(customer_id="C-1001")
    assert result["verified"] is True
    assert result["customer"]["name"] == "Ada Lovelace"


def test_get_customer_no_match_returns_validation_error():
    result = get_customer(customer_id="C-9999")
    assert result["isError"] is True
    assert result["errorCategory"] == "validation"
    assert result["isRetryable"] is False


def test_get_customer_requires_at_least_one_identifier():
    result = get_customer()
    assert result["isError"] is True
    assert result["errorCategory"] == "validation"


def test_lookup_order_validates_format():
    result = lookup_order("5001")  # missing "O-" prefix
    assert result["isError"] is True
    assert result["errorCategory"] == "validation"


def test_process_refund_rejects_amount_above_order():
    result = process_refund("O-5001", amount_usd=999.99, reason="test")
    assert result["isError"] is True
    assert result["errorCategory"] == "validation"


def test_escalate_returns_structured_handoff():
    result = escalate_to_human(
        customer_id="C-1001",
        summary="Customer wants refund on damaged item.",
        root_cause="Item arrived broken; photos confirm damage.",
        recommended_action="Approve full refund of $249.99.",
        refund_amount_usd=249.99,
    )
    assert "ticket_id" in result
    assert result["handoff"]["customer_id"] == "C-1001"

# --- Adversarial tests aligned to exam anti-patterns ---

def test_get_customer_with_multiple_matches_does_not_auto_pick():
    """Task Statement 5.2: 'Instructing the agent to ask for additional
    identifiers when tool results return multiple matches, rather than
    selecting based on heuristics.'
    
    We add a duplicate-email customer to test this scenario.
    """
    from src import backend
    backend.CUSTOMERS["C-9001"] = {
        "id": "C-9001",
        "name": "Ada Lovelace",  # same name, different ID
        "email": "test1001@example.com",  # SAME email as C-1001
        "verified_at": "2025-01-01T00:00:00Z",
        "tier": "standard",
    }
    try:
        result = get_customer(email="test1001@example.com")
        # Tool must surface ambiguity, not pick one
        assert result.get("needs_clarification") is True
        assert len(result["matches"]) == 2
        assert result["verified"] is False
    finally:
        # Clean up so other tests aren't affected
        del backend.CUSTOMERS["C-9001"]


def test_error_responses_have_consistent_shape():
    """Every error path must return the same keys so the agent
    can write one recovery handler, not four. (Task Statement 2.2)"""
    error_results = [
        get_customer(),                                         # validation
        get_customer(customer_id="C-NOPE"),                     # validation
        lookup_order("5001"),                                   # validation (bad format)
        lookup_order("O-NOPE"),                                 # validation (not found)
        process_refund("O-5001", amount_usd=-5.0, reason="x"),  # validation
        process_refund("O-NOPE", amount_usd=10.0, reason="x"),  # validation
        process_refund("O-5001", amount_usd=99999.0, reason="x"),  # validation
    ]
    required_keys = {"isError", "errorCategory", "isRetryable", "message"}
    for r in error_results:
        assert required_keys.issubset(r.keys()), f"Missing keys in: {r}"
        assert r["isError"] is True
        assert r["errorCategory"] in {"transient", "validation", "business", "permission"}


def test_validation_errors_are_not_retryable():
    """Retrying the same invalid input will fail the same way.
    This shape lets the agent skip wasted retries (Task Statement 2.2)."""
    result = lookup_order("not-a-real-format")
    assert result["isRetryable"] is False


def test_lookup_order_returns_all_fields_for_filtering_downstream():
    """The tool returns everything; trimming happens in the hook layer.
    This is the setup for Task Statement 5.1: trimming verbose tool
    outputs before they accumulate in context.
    
    We verify the noisy fields exist so Milestone 4's normalization
    has something to normalize.
    """
    result = lookup_order("O-5001")
    order = result["order"]
    assert "placed_at_epoch" in order   # Unix int (noisy)
    assert "items" in order              # nested array
    assert "amount_usd" in order         # the field the agent actually needs


def test_escalate_requires_complete_handoff():
    """Task Statement 1.4: 'Compiling structured handoff summaries...
    when escalating to human agents who lack access to the conversation
    transcript.' An incomplete handoff must fail loudly, not silently
    create an empty ticket.
    """
    result = escalate_to_human(
        customer_id="C-1001",
        summary="",                  # empty — should fail
        root_cause="something",
        recommended_action="something",
    )
    assert result["isError"] is True
    assert result["errorCategory"] == "validation"