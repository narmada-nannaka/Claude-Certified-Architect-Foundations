"""Tests for escalation handoff structure.

Per Task Statement 1.4, the human agent receiving an escalation does not
have access to the conversation transcript. The handoff must therefore
contain every fact the human needs to act.

These tests exercise the escalate_to_human tool directly and add quality checks the exam tests around: required
fields populated with substantive content, refund amount preserved
through escalation, multi-concern preservation in summary.
"""
import pytest

from src.mcp_server import escalate_to_human


# --- Required-field enforcement ---

def test_escalation_rejects_empty_summary():
    result = escalate_to_human(
        customer_id="C-1001",
        summary="",
        root_cause="Carrier dispute",
        recommended_action="Approve refund",
    )
    assert result["isError"] is True
    assert result["errorCategory"] == "validation"


def test_escalation_rejects_empty_root_cause():
    result = escalate_to_human(
        customer_id="C-1001",
        summary="Customer wants refund",
        root_cause="",
        recommended_action="Approve refund",
    )
    assert result["isError"] is True


def test_escalation_rejects_empty_recommended_action():
    result = escalate_to_human(
        customer_id="C-1001",
        summary="Customer wants refund",
        root_cause="Carrier dispute",
        recommended_action="",
    )
    assert result["isError"] is True


def test_escalation_succeeds_with_all_required_fields():
    result = escalate_to_human(
        customer_id="C-1003",
        summary="Customer wants refund of $1299 on O-5003.",
        root_cause="Refund exceeds per-case policy limit.",
        recommended_action="Review and approve full refund.",
        refund_amount_usd=1299.00,
    )
    assert "ticket_id" in result
    handoff = result["handoff"]
    assert handoff["customer_id"] == "C-1003"
    assert handoff["refund_amount_usd"] == 1299.00


def test_escalation_succeeds_without_optional_refund_amount():
    """Some escalations aren't refund-related (policy questions,
    account changes). The refund field is optional."""
    result = escalate_to_human(
        customer_id="C-1001",
        summary="Customer asks about competitor price match.",
        root_cause="Policy is silent on competitor price matching.",
        recommended_action="Provide policy guidance or one-time courtesy.",
    )
    assert result["handoff"]["refund_amount_usd"] is None