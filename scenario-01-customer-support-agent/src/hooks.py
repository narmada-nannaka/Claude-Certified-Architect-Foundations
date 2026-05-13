"""Hooks for the customer support agent.

Implements Task Statement 1.5 patterns:
- PostToolUse hook for data normalization 
- PreToolUse hook for policy enforcement and prerequisite gating 

Hooks intercept the tool call lifecycle at well-defined points and apply
deterministic transformations. They are the exam's correct answer when
the alternative is 'add an instruction to the system prompt.'
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


# --- Normalization primitives (pure functions, easy to test) ---

REFUND_STATUS_CODE_TO_NAME = {
    0: "pending",
    1: "completed",
    2: "rejected",
}


def epoch_to_iso(epoch_seconds: int | float) -> str:
    """Convert a Unix epoch timestamp to an ISO 8601 string.

    The model reasons about ISO dates far more reliably than epochs.
    Returning '2024-03-12T14:22:00+00:00' makes 'when was this ordered?'
    a one-step inference, not a multi-step calculation.
    """
    dt = datetime.fromtimestamp(epoch_seconds, tz=timezone.utc)
    return dt.isoformat()


def normalize_order_result(result: dict) -> dict:
    """Normalize the shape of a lookup_order result.

    Operations:
    - Convert placed_at_epoch (Unix int) to placed_at_iso (ISO string).
    - Keep placed_at_epoch as well, marked with a __raw__ suffix, so
      anything that needs the original value can still access it. This
      is the Postel's-law principle: never destroy source data.
    """
    if "order" not in result:
        return result  # Likely an error response; leave untouched.

    order = dict(result["order"])  # shallow copy
    if "placed_at_epoch" in order:
        order["placed_at_iso"] = epoch_to_iso(order["placed_at_epoch"])
        order["__raw_placed_at_epoch"] = order.pop("placed_at_epoch")

    return {**result, "order": order}


def normalize_refund_result(result: dict) -> dict:
    """Normalize the shape of a process_refund result.

    Operations:
    - Convert status_code (int) to status (string name).
    - Convert created_at_epoch to created_at_iso.
    - Preserve raw values under __raw_ prefixed keys.
    """
    if "refund" not in result:
        return result

    refund = dict(result["refund"])

    if "status_code" in refund:
        code = refund["status_code"]
        refund["status"] = REFUND_STATUS_CODE_TO_NAME.get(code, f"unknown_code_{code}")
        refund["__raw_status_code"] = refund.pop("status_code")

    if "created_at_epoch" in refund:
        refund["created_at_iso"] = epoch_to_iso(refund["created_at_epoch"])
        refund["__raw_created_at_epoch"] = refund.pop("created_at_epoch")

    return {**result, "refund": refund}


def normalize_customer_result(result: dict) -> dict:
    """Normalize the shape of a get_customer result.

    The customer system already uses ISO 8601, so the main work here is
    trimming verbose fields that the agent doesn't need for typical
    decisions. This implements Task 5.1's 'Trimming verbose tool outputs
    to only relevant fields before they accumulate in context.'

    We keep the trimmed fields under __raw_full__ for debug visibility.
    """
    if not result.get("verified"):
        return result  # Multi-match or error case — preserve as-is.

    customer = dict(result["customer"])
    full_record = dict(customer)
    # Keep what the agent actually needs for downstream decisions.
    trimmed = {
        "id": customer["id"],
        "name": customer["name"],
        "email": customer["email"],
        "verified_at": customer["verified_at"],
        "tier": customer["tier"],
    }
    # In our fixture all fields are 'relevant' so the trim is a no-op,
    # but in a real system you'd drop things like marketing preferences,
    # cookie IDs, A/B test buckets, etc.
    return {
        **result,
        "customer": trimmed,
        "__raw_full_customer": full_record,
    }


# --- The PostToolUse hook itself ---

# Registry mapping tool name → normalizer.
# Adding a new tool's normalizer is one line; no loop changes needed.
POST_TOOL_USE_NORMALIZERS = {
    "lookup_order": normalize_order_result,
    "process_refund": normalize_refund_result,
    "get_customer": normalize_customer_result,
}


def post_tool_use_hook(tool_name: str, tool_result: dict) -> dict:
    """PostToolUse hook entry point.

    Called by the agent loop AFTER a tool returns its result but BEFORE
    the result is wrapped into a tool_result block and sent back to
    the model. This is the deterministic transformation point.

    Args:
        tool_name: the name of the tool that just ran.
        tool_result: the raw result the tool returned.

    Returns:
        The (possibly transformed) result that the model will see.
    """
    # Never normalize error responses. They have a fixed structure
    # (Task 2.2's errorCategory/isRetryable) that the agent depends on.
    if tool_result.get("isError"):
        return tool_result

    normalizer = POST_TOOL_USE_NORMALIZERS.get(tool_name)
    if normalizer is None:
        return tool_result  # No-op for tools we don't normalize.

    return normalizer(tool_result)

    # --- PreToolUse hook for prerequisite gating ---

# Tools that require a verified customer in session before they can run.
# Centralized so adding a new gated tool is one line, not a code change.
GATED_TOOLS = {"lookup_order", "process_refund"}

# Refund cap policy (read from env in real systems; hardcoded for demos).
REFUND_LIMIT_USD = 500.0


class SessionState:
    """Tracks per-session facts that hooks consult and update.

    In the real Claude Agent SDK this would be `context.session_state` —
    a dict-like object the SDK passes to every hook. We build a minimal
    version here so the agent loop has somewhere to keep cross-tool
    facts without polluting the message history.

    Per Task Statement 5.1, this is also the natural home for the
    'case facts' block — verified IDs, amounts, key dates — that we
    want to persist outside the summarized conversation history.
    """

    def __init__(self):
        self.verified_customer_id: str | None = None
        self.verified_customer_name: str | None = None
        # Track what each gated tool's call attempted (useful for logging)
        self.gate_violations: list[dict] = []

    def mark_customer_verified(self, customer_id: str, name: str):
        self.verified_customer_id = customer_id
        self.verified_customer_name = name

    def reset(self):
        """Clear session state. Call when starting a new customer interaction."""
        self.verified_customer_id = None
        self.verified_customer_name = None
        self.gate_violations.clear()


def pre_tool_use_hook(
    tool_name: str,
    tool_input: dict,
    session: SessionState,
) -> tuple[bool, dict | None]:
    """PreToolUse hook: enforce prerequisites and policy gates.

    Returns:
        (allow, replacement_result)
        - allow=True, replacement=None → let the tool run.
        - allow=False, replacement=<dict> → block the call; return the
          replacement dict as if it were the tool's result. The replacement
          is always a structured business error so the agent can recover
          (typically by calling get_customer first, or by escalating).

    The dual responsibilities of this hook:
      1. Identity-verification prerequisite (Task 1.4 / Sample Question 1)
      2. Refund policy limit (Task 1.5 / Sample Question 1 rationale)

    Both follow the same pattern: detect a violation, return a structured
    business error explaining the issue, so the agent's next reasoning
    step has the information it needs to recover.
    """

    # --- Prerequisite gate: verify customer before gated tools ---
    if tool_name in GATED_TOOLS and session.verified_customer_id is None:
        session.gate_violations.append({
            "tool": tool_name,
            "violation": "prerequisite",
            "input": tool_input,
        })
        return (False, {
            "isError": True,
            "errorCategory": "business",
            "isRetryable": False,
            "message": (
                f"Cannot call {tool_name} yet: customer identity has not "
                f"been verified in this session. Call get_customer first "
                f"with the customer's ID or email, then retry."
            ),
            "detail": "PreToolUse hook blocked the call due to unmet prerequisite.",
        })

    # --- Policy gate: refund limit enforcement ---
    if tool_name == "process_refund":
        amount = tool_input.get("amount_usd", 0)
        if amount > REFUND_LIMIT_USD:
            session.gate_violations.append({
                "tool": tool_name,
                "violation": "amount_over_limit",
                "input": tool_input,
            })
            return (False, {
                "isError": True,
                "errorCategory": "business",
                "isRetryable": False,
                "message": (
                    f"Refund of ${amount:.2f} exceeds the per-case limit of "
                    f"${REFUND_LIMIT_USD:.2f}. This must be escalated to a "
                    f"human agent via escalate_to_human."
                ),
                "detail": (
                    f"PreToolUse hook blocked the call: amount={amount} "
                    f"limit={REFUND_LIMIT_USD}"
                ),
            })

        # --- Cross-check: refund must be for the verified customer ---
        # (We could only check this if we held the order's customer_id in
        # session state. Adding this requires also recording lookup_order
        # results in session — a worthwhile exercise. For now, we limit
        # ourselves to the two violations above to keep the gate focused.)

    return (True, None)


def update_session_from_result(
    tool_name: str,
    tool_result: dict,
    session: SessionState,
) -> None:
    """Update session state based on a (successful) tool result.

    This is the companion to pre_tool_use_hook — it's what records facts
    so subsequent hook checks have something to consult. Called after
    PostToolUse normalization so it sees the canonical fields.
    """
    if tool_result.get("isError"):
        return  # Errors don't update state — the verification didn't happen.

    if tool_name == "get_customer" and tool_result.get("verified"):
        customer = tool_result["customer"]
        session.mark_customer_verified(
            customer_id=customer["id"],
            name=customer["name"],
        )