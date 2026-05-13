"""Custom MCP server exposing customer support tools.

Tool descriptions follow Task Statement 2.1 best practices:
- Purpose stated clearly
- Input format specified
- Example queries provided
- Boundary conditions explained
- Differentiation from similar tools

These tools are intentionally distinct in purpose to avoid the
misrouting problem from Sample Question 2.
"""
from mcp.server.fastmcp import FastMCP

from . import backend
from .errors import (
    business_error,
    transient_error,
    validation_error,
)

mcp = FastMCP("customer-support")


@mcp.tool()
def get_customer(customer_id: str | None = None,
                 email: str | None = None) -> dict:
    """Verify customer identity and retrieve their account profile.

    MANDATORY FIRST STEP: Call this tool as the FIRST tool in any session —
    even before asking the customer for their ID. If the customer has not yet
    provided their customer_id or email, call this tool with no arguments.
    The error response will tell you what credentials to request; do NOT skip
    this call and respond with plain text instead.

    Call order rule: get_customer MUST be called before lookup_order,
    process_refund, or any other tool. Never call those tools first.

    Inputs (provide at most one):
      - customer_id: format "C-NNNN" (e.g., "C-1001")
      - email: full email address (e.g., "[email protected]")
      - (no arguments): begins the identity-gathering step

    Returns:
      On single match: {"customer": {...}, "verified": true}
      On multiple matches: {"matches": [...], "verified": false, "needs_clarification": true}
      On no match or missing args: validation error describing what is needed

    Do NOT use this tool to look up orders — use lookup_order for that.
    Do NOT call lookup_order or process_refund before this tool returns verified=true.
    """
    if not customer_id and not email:
        return validation_error(
            "Either a valid customer_id or email must be provided.",
            detail="Empty arguments to get_customer.",
        )

    matches = backend.find_customer(customer_id=customer_id, email=email)

    if not matches:
        return validation_error(
            "No customer found with the provided identifier(s).",
            detail=f"Searched customer_id={customer_id}, email={email}",
        )

    if len(matches) > 1:
        # Task Statement 5.2: ask for clarification, do NOT heuristically pick.
        return {
            "matches": [{"id": m["id"], "name": m["name"]} for m in matches],
            "verified": False,
            "needs_clarification": True,
            "message": "Multiple customers matched. Ask for an additional identifier.",
        }

    return {"customer": matches[0], "verified": True}


@mcp.tool()
def lookup_order(order_id: str) -> dict:
    """Retrieve full details of a single order by its order ID.

    Use this tool when you have a specific order ID (format "O-NNNN") and
    need the order's status, items, amount, or placement date. This tool
    returns ALL fields for the order; downstream processing should filter
    to what's relevant.

    Input:
      - order_id: format "O-NNNN" (e.g., "O-5001"). The leading "O-" is required.

    Returns the order record including customer_id, amount_usd, status,
    placed_at_epoch (Unix timestamp), and line items.

    Do NOT use this tool to find customers — use get_customer for that.
    Do NOT use this tool to issue a refund — use process_refund for that.
    """
    if not order_id or not order_id.startswith("O-"):
        return validation_error(
            "order_id must be in format 'O-NNNN'.",
            detail=f"Received: {order_id!r}",
        )

    order = backend.find_order(order_id)
    if not order:
        return validation_error(
            f"Order {order_id} was not found.",
            detail="Order ID not in database.",
        )

    return {"order": order}


@mcp.tool()
def process_refund(order_id: str, amount_usd: float, reason: str) -> dict:
    """Issue a refund against a specific order.

    PREREQUISITES enforced by hook:
      - get_customer must have returned a verified customer in this session
      - The order's customer_id must match the verified customer

    Inputs:
      - order_id: format "O-NNNN"
      - amount_usd: positive number, must not exceed the order's amount_usd
      - reason: short customer-facing reason (e.g., "damaged on arrival")

    Returns:
      On success: refund record with refund_id, status_code, created_at_epoch.
      On policy violation (amount exceeds REFUND_LIMIT_USD): business error,
        non-retryable, with instruction to escalate.
    """
    if amount_usd <= 0:
        return validation_error("Refund amount must be positive.")

    order = backend.find_order(order_id)
    if not order:
        return validation_error(f"Order {order_id} not found; cannot refund.")

    if amount_usd > order["amount_usd"]:
        return validation_error(
            "Refund amount exceeds the order total.",
            detail=f"order amount={order['amount_usd']}, requested={amount_usd}",
        )

    # Note: the >$500 policy check is enforced by the PreToolUse hook,
    # not here. That separation is intentional.
    refund = backend.create_refund(order_id, amount_usd)
    return {"refund": refund, "reason": reason}


@mcp.tool()
def escalate_to_human(
    summary: str,
    root_cause: str,
    recommended_action: str,
    customer_id: str | None = None,
    refund_amount_usd: float | None = None,
) -> dict:
    """Hand the case off to a human agent with a structured summary.

    Per Task Statement 1.4, the human agent does NOT have access to the
    conversation transcript. The handoff must be self-contained.

    Use this tool IMMEDIATELY when:
      - The customer explicitly asks for a human (honor this without delay)
      - Policy is silent or ambiguous on the customer's request
      - The agent cannot make meaningful progress
      - A business rule was hit (e.g., refund exceeds policy limit)

    When the customer asks for a human agent, call this tool right away —
    do NOT ask for more information first or respond with plain text.

    Inputs:
      - summary (required): 1-2 sentences describing what the customer wants
      - root_cause (required): 1-2 sentences on the underlying issue
      - recommended_action (required): what the human should do next
      - customer_id (optional): verified customer ID if known
      - refund_amount_usd (optional): refund amount if applicable

    Returns the ticket ID and queue position. Do NOT call any other tools
    after this — the case has been transferred.
    """
    if not all([summary, root_cause, recommended_action]):
        return validation_error(
            "summary, root_cause, and recommended_action are required.",
            detail="Missing one of: summary, root_cause, recommended_action.",
        )

    return {
        "ticket_id": "T-77001",
        "queue": "tier-2",
        "estimated_wait_minutes": 8,
        "handoff": {
            "customer_id": customer_id,
            "summary": summary,
            "root_cause": root_cause,
            "recommended_action": recommended_action,
            "refund_amount_usd": refund_amount_usd,
        },
    }

@mcp.tool()
def track_shipment(order_id: str) -> dict:
    """Get the current shipment tracking details for an order in transit.

    Use this tool when the customer asks "where is my package", "when will
    my order arrive", or similar shipping-status questions. This tool ONLY
    returns useful data for orders that are currently in transit; for
    delivered or pending orders it returns a validation error.

    Input:
      - order_id: format "O-NNNN"

    Returns the carrier name, tracking number, last scan location, and
    estimated delivery date (ISO 8601).

    Do NOT use this tool to check whether an order exists — use lookup_order
    for that. Do NOT use this tool for delivered orders — their status is
    already visible in lookup_order's response.
    """
    if not order_id or not order_id.startswith("O-"):
        return validation_error(
            "order_id must be in format 'O-NNNN'.",
            detail=f"Received: {order_id!r}",
        )

    tracking = backend.get_shipment_tracking(order_id)
    if not tracking:
        return validation_error(
            f"No active shipment tracking for {order_id}. The order may "
            f"already be delivered or not yet shipped.",
            detail="track_shipment requires an in-transit order.",
        )

    return {"tracking": tracking}


if __name__ == "__main__":
    mcp.run()