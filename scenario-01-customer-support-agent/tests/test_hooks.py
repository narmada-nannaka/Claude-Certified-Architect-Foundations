"""Tests for normalization hooks.

We test the hook functions directly (no loop, no API) because normalization
is a pure data transformation. The loop integration is tested separately
in test_agent_loop.py.
"""
import pytest

from src.hooks import (
    epoch_to_iso,
    normalize_customer_result,
    normalize_order_result,
    normalize_refund_result,
    post_tool_use_hook,
)


# --- epoch_to_iso primitive ---

def test_epoch_to_iso_known_value():
    # 1709913600 = 2024-03-08T16:00:00Z (verifiable independently)
    assert epoch_to_iso(1709913600) == "2024-03-08T16:00:00+00:00"


def test_epoch_to_iso_zero_is_unix_epoch_start():
    assert epoch_to_iso(0) == "1970-01-01T00:00:00+00:00"


# --- normalize_order_result ---

def test_normalize_order_adds_iso_field_and_preserves_raw():
    raw = {
        "order": {
            "order_id": "O-5001",
            "customer_id": "C-1001",
            "amount_usd": 249.99,
            "placed_at_epoch": 1709913600,
            "status": "delivered",
        }
    }
    normalized = normalize_order_result(raw)
    order = normalized["order"]
    # Canonical ISO field is present...
    assert order["placed_at_iso"] == "2024-03-08T16:00:00+00:00"
    # ...and the raw value is preserved for debugging.
    assert order["__raw_placed_at_epoch"] == 1709913600
    # The original epoch key is gone so the model doesn't see two
    # competing date fields.
    assert "placed_at_epoch" not in order


def test_normalize_order_passes_error_through_untouched():
    """Errors must not be reshaped — they have their own contract."""
    err = {
        "isError": True,
        "errorCategory": "validation",
        "isRetryable": False,
        "message": "order not found",
    }
    assert normalize_order_result(err) == err


# --- normalize_refund_result ---

def test_normalize_refund_translates_status_code():
    raw = {
        "refund": {
            "refund_id": "R-9001",
            "order_id": "O-5001",
            "amount_usd": 50.0,
            "status_code": 0,
            "created_at_epoch": 1715184000,
        },
        "reason": "scratch"
    }
    normalized = normalize_refund_result(raw)
    refund = normalized["refund"]
    assert refund["status"] == "pending"
    assert refund["__raw_status_code"] == 0
    assert "status_code" not in refund
    assert refund["created_at_iso"] == "2024-05-08T16:00:00+00:00"


def test_normalize_refund_handles_unknown_status_code():
    """An unmapped status code shouldn't crash — it should be visible
    as 'unknown' so the agent can flag it rather than silently mislabel."""
    raw = {"refund": {"status_code": 99, "created_at_epoch": 1715184000}}
    normalized = normalize_refund_result(raw)
    assert normalized["refund"]["status"] == "unknown_code_99"


# --- normalize_customer_result ---

def test_normalize_customer_preserves_full_record_under_raw():
    raw = {
        "customer": {
            "id": "C-1001",
            "name": "Ada Lovelace",
            "email": "[email protected]",
            "verified_at": "2024-03-12T14:22:00Z",
            "tier": "gold",
            # imagine these came from the customer table too:
            "marketing_consent": True,
            "ab_test_buckets": ["x", "y"],
        },
        "verified": True,
    }
    normalized = normalize_customer_result(raw)
    # The trimmed view is what the model sees.
    assert "marketing_consent" not in normalized["customer"]
    # But the full record is preserved.
    assert normalized["__raw_full_customer"]["marketing_consent"] is True


def test_normalize_customer_passes_multi_match_through():
    """needs_clarification responses are not errors but also not
    'verified' — the customer block doesn't exist on these. Hook must
    leave the response shape intact so the agent can detect clarification."""
    raw = {
        "matches": [{"id": "C-1001", "name": "Ada"}, {"id": "C-9001", "name": "Ada"}],
        "verified": False,
        "needs_clarification": True,
    }
    normalized = normalize_customer_result(raw)
    assert normalized == raw


# --- post_tool_use_hook dispatcher ---

def test_dispatcher_routes_to_correct_normalizer():
    raw_order = {"order": {"order_id": "O-1", "placed_at_epoch": 1700000000}}
    result = post_tool_use_hook("lookup_order", raw_order)
    assert "placed_at_iso" in result["order"]


def test_dispatcher_is_noop_for_unregistered_tool():
    raw = {"some": "data"}
    result = post_tool_use_hook("unknown_tool_xyz", raw)
    assert result == raw


def test_dispatcher_skips_error_responses_even_for_registered_tools():
    err = {
        "isError": True,
        "errorCategory": "transient",
        "isRetryable": True,
        "message": "timeout",
    }
    # Even though lookup_order has a normalizer, errors must pass through.
    result = post_tool_use_hook("lookup_order", err)
    assert result == err