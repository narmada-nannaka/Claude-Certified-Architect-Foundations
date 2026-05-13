"""Tests for the PreToolUse prerequisite gate.

Per Task Statement 1.4, the gate provides deterministic guarantees that
prompt instructions cannot. These tests verify that the guarantee holds
under every input pattern the model might produce.
"""
import pytest

from src.hooks import (
    REFUND_LIMIT_USD,
    SessionState,
    pre_tool_use_hook,
    update_session_from_result,
)


# --- Identity-verification prerequisite ---

def test_lookup_order_blocked_when_no_customer_verified():
    """The exact Sample Question 1 pattern: lookup_order before get_customer."""
    session = SessionState()
    allow, replacement = pre_tool_use_hook(
        "lookup_order",
        {"order_id": "O-5001"},
        session,
    )
    assert allow is False
    assert replacement["isError"] is True
    assert replacement["errorCategory"] == "business"
    assert replacement["isRetryable"] is False
    assert "get_customer" in replacement["message"]


def test_process_refund_blocked_when_no_customer_verified():
    session = SessionState()
    allow, replacement = pre_tool_use_hook(
        "process_refund",
        {"order_id": "O-5001", "amount_usd": 50.0, "reason": "scratch"},
        session,
    )
    assert allow is False
    assert replacement["errorCategory"] == "business"


def test_get_customer_itself_is_not_gated():
    """The prerequisite tool must be allowed; otherwise nobody can ever
    get past the gate. This guards against an off-by-one bug where
    someone adds get_customer to GATED_TOOLS by accident."""
    session = SessionState()
    allow, replacement = pre_tool_use_hook(
        "get_customer",
        {"customer_id": "C-1001"},
        session,
    )
    assert allow is True
    assert replacement is None


def test_escalate_to_human_is_not_gated():
    """Escalation must be available regardless of verification state.
    A customer who shouts 'GET ME A HUMAN' before saying anything else
    shouldn't be forced through identity verification first."""
    session = SessionState()
    allow, _ = pre_tool_use_hook(
        "escalate_to_human",
        {
            "customer_id": "unknown",
            "summary": "Customer demanded human",
            "root_cause": "Frustration",
            "recommended_action": "Take the call",
        },
        session,
    )
    assert allow is True


def test_lookup_order_allowed_after_customer_verified():
    session = SessionState()
    # Simulate get_customer returning a verified customer
    update_session_from_result(
        "get_customer",
        {"customer": {"id": "C-1001", "name": "Ada Lovelace"}, "verified": True},
        session,
    )
    assert session.verified_customer_id == "C-1001"

    allow, _ = pre_tool_use_hook(
        "lookup_order",
        {"order_id": "O-5001"},
        session,
    )
    assert allow is True


def test_failed_get_customer_does_not_satisfy_prerequisite():
    """A get_customer that returned an error or needs_clarification is NOT
    a verified customer. The gate must still block downstream tools."""
    session = SessionState()
    # Simulate get_customer returning a needs-clarification response
    update_session_from_result(
        "get_customer",
        {"matches": [{"id": "C-1"}, {"id": "C-2"}], "verified": False},
        session,
    )
    assert session.verified_customer_id is None

    allow, _ = pre_tool_use_hook("lookup_order", {"order_id": "O-1"}, session)
    assert allow is False


def test_get_customer_validation_error_does_not_satisfy_prerequisite():
    session = SessionState()
    # Simulate get_customer returning a validation error
    update_session_from_result(
        "get_customer",
        {
            "isError": True,
            "errorCategory": "validation",
            "isRetryable": False,
            "message": "No customer found",
        },
        session,
    )
    assert session.verified_customer_id is None

    allow, _ = pre_tool_use_hook("lookup_order", {"order_id": "O-1"}, session)
    assert allow is False


# --- Refund-limit policy gate ---

def test_refund_at_limit_is_allowed():
    """Boundary test: exactly $500 should pass; only amounts ABOVE $500
    are blocked. Off-by-one bugs here have real money consequences."""
    session = SessionState()
    update_session_from_result(
        "get_customer",
        {"customer": {"id": "C-1001", "name": "Ada"}, "verified": True},
        session,
    )
    allow, _ = pre_tool_use_hook(
        "process_refund",
        {"order_id": "O-1", "amount_usd": REFUND_LIMIT_USD, "reason": "x"},
        session,
    )
    assert allow is True


def test_refund_above_limit_is_blocked():
    session = SessionState()
    update_session_from_result(
        "get_customer",
        {"customer": {"id": "C-1001", "name": "Ada"}, "verified": True},
        session,
    )
    allow, replacement = pre_tool_use_hook(
        "process_refund",
        {"order_id": "O-1", "amount_usd": REFUND_LIMIT_USD + 0.01, "reason": "x"},
        session,
    )
    assert allow is False
    assert "escalate_to_human" in replacement["message"]


def test_refund_above_limit_is_blocked_even_when_verified():
    """Both gates can fire on the same call; either one blocks.
    Verifying the customer doesn't unlock above-limit refunds."""
    session = SessionState()
    update_session_from_result(
        "get_customer",
        {"customer": {"id": "C-1001", "name": "Ada"}, "verified": True},
        session,
    )
    allow, replacement = pre_tool_use_hook(
        "process_refund",
        {"order_id": "O-1", "amount_usd": 1_000.0, "reason": "x"},
        session,
    )
    assert allow is False
    assert replacement["errorCategory"] == "business"


# --- Session state hygiene ---

def test_session_reset_clears_verification():
    """After a session reset (new customer), the gate must block again.
    Otherwise, the gate has a state-leak vulnerability."""
    session = SessionState()
    update_session_from_result(
        "get_customer",
        {"customer": {"id": "C-1001", "name": "Ada"}, "verified": True},
        session,
    )
    session.reset()
    allow, _ = pre_tool_use_hook("lookup_order", {"order_id": "O-1"}, session)
    assert allow is False


def test_gate_violations_are_recorded():
    """Observability: every blocked call should leave a trace for logs."""
    session = SessionState()
    pre_tool_use_hook("lookup_order", {"order_id": "O-1"}, session)
    pre_tool_use_hook("process_refund", {"order_id": "O-1", "amount_usd": 50}, session)
    assert len(session.gate_violations) == 2
    assert session.gate_violations[0]["tool"] == "lookup_order"
    assert session.gate_violations[0]["violation"] == "prerequisite"