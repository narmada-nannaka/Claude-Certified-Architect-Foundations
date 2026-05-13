"""Agentic loop for the customer support resolution agent.

Implements Task Statement 1.1 correctly:
- Continues when stop_reason == "tool_use"
- Terminates when stop_reason == "end_turn"
- Appends tool results to conversation history between iterations
- Does NOT parse natural language to decide when to stop
- Does NOT use iteration caps as the primary termination mechanism
  (a safety cap exists, but it's a circuit breaker, not the control flow)
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any

from anthropic import Anthropic
from dotenv import load_dotenv

from .mcp_server import (
    escalate_to_human,
    get_customer,
    lookup_order,
    process_refund,
    track_shipment,
)
from .prompts import SYSTEM_PROMPT

from .hooks import (
    SessionState,
    post_tool_use_hook,
    pre_tool_use_hook,
    update_session_from_result,
)

load_dotenv()

# Registry of tool names → callable implementations.
# In a real MCP setup, the Agent SDK would dispatch through the MCP
# transport. For this teaching scaffold we dispatch in-process so we
# can step through the loop in a debugger.
TOOL_IMPLEMENTATIONS = {
    "get_customer": get_customer,
    "lookup_order": lookup_order,
    "process_refund": process_refund,
    "escalate_to_human": escalate_to_human,
    "track_shipment": track_shipment,
}

# Tool schemas in Claude's tool-use format.
# Note: in production you'd generate these from the MCP server's tool
# discovery response; we declare them explicitly here for clarity.
TOOL_SCHEMAS = [
    {
        "name": "get_customer",
        "description": get_customer.__doc__,
        "input_schema": {
            "type": "object",
            "properties": {
                "customer_id": {"type": "string"},
                "email": {"type": "string"},
            },
        },
    },
    {
        "name": "lookup_order",
        "description": lookup_order.__doc__,
        "input_schema": {
            "type": "object",
            "properties": {"order_id": {"type": "string"}},
            "required": ["order_id"],
        },
    },
    {
        "name": "process_refund",
        "description": process_refund.__doc__,
        "input_schema": {
            "type": "object",
            "properties": {
                "order_id": {"type": "string"},
                "amount_usd": {"type": "number"},
                "reason": {"type": "string"},
            },
            "required": ["order_id", "amount_usd", "reason"],
        },
    },
    {
        "name": "escalate_to_human",
        "description": escalate_to_human.__doc__,
        "input_schema": {
            "type": "object",
            "properties": {
                "customer_id": {"type": "string"},
                "summary": {"type": "string"},
                "root_cause": {"type": "string"},
                "recommended_action": {"type": "string"},
                "refund_amount_usd": {"type": "number"},
            },
            "required": ["customer_id", "summary", "root_cause", "recommended_action"],
        },
    },
    {
        "name": "track_shipment",
        "description": track_shipment.__doc__,
        "input_schema": {
            "type": "object",
            "properties": {"order_id": {"type": "string"}},
            "required": ["order_id"],
        },
    },
]

MODEL = "claude-sonnet-4-5"
MAX_ITERATIONS_SAFETY_CAP = 25  # Circuit breaker, NOT the primary stop


@dataclass
class AgentRun:
    """Captures everything that happened in one user turn.

    Useful for tests and for the demo script's transcript output.
    """
    final_text: str = ""
    iterations: int = 0
    tool_calls: list[dict] = field(default_factory=list)
    stop_reason: str = ""
    hit_safety_cap: bool = False
    gate_violations: list[dict] = field(default_factory=list)


def run_agent(user_message: str,
              conversation_history: list[dict] | None = None,
              session: SessionState | None = None,
              ) -> tuple[AgentRun, list[dict], SessionState]:
    """Run the agentic loop until the model signals end_turn.

    Args:
        user_message: the new user input for this turn.
        conversation_history: prior messages (assistant + user + tool_result).
            Pass None for a fresh session.
        session: pre-session mutable state. Pass None for a fresh session;
            Pass the returned SessionState back in to continue.

    Returns:
        (AgentRun summary, updated conversation_history, session_state).
        The updated history can be passed to the next call to continue
        the conversation.
    """
    client = Anthropic()
    messages = list(conversation_history or [])
    messages.append({"role": "user", "content": user_message})

    if session is None:
        session = SessionState()

    run = AgentRun()

    while True:
        run.iterations += 1

        # SAFETY CAP — not the primary termination condition.
        # If we hit this, something is wrong (infinite tool-call loop).
        # The exam (Task 1.1) warns against using iteration caps as the
        # PRIMARY stopping mechanism. Here it's a circuit breaker only.
        if run.iterations > MAX_ITERATIONS_SAFETY_CAP:
            run.hit_safety_cap = True
            run.final_text = (
                "[Safety cap reached. Conversation terminated to prevent runaway loop.]"
            )
            break

        response = client.messages.create(
            model=MODEL,
            max_tokens=2048,
            system=SYSTEM_PROMPT,
            tools=TOOL_SCHEMAS,
            messages=messages,
        )

        run.stop_reason = response.stop_reason

        # The assistant's response (which may contain text and/or tool_use
        # blocks) goes into history as-is. This is required so the next
        # API call sees what the model just decided.
        messages.append({"role": "assistant", "content": response.content})

        # === THE TERMINATION CHECK ===
        # Task Statement 1.1, correct pattern:
        #   - "end_turn" → model is done, return its text to user
        #   - "tool_use" → model wants to call tools, execute and continue
        # We do NOT look at response.content for "looks like a final answer"
        # signals. We do NOT parse natural language. The stop_reason field
        # is the authoritative termination signal.
        if response.stop_reason == "end_turn":
            # Extract the final text for the user.
            run.final_text = _extract_text(response.content)
            break

        if response.stop_reason == "tool_use":
            # Execute every tool_use block in the response, in order.
            # A single response may contain multiple tool_use blocks
            # (parallel tool calls); we honor that.
            tool_results = []
            for block in response.content:
                if block.type != "tool_use":
                    continue

                tool_name = block.name
                tool_input = block.input
                tool_use_id = block.id

                # === PReToolUse hook ===
                allow, replacement = pre_tool_use_hook(tool_name, tool_input, session)

                if not allow:
                    # Hook blocked the call. Use the replacement as the result. 
                    result = replacement
                    # Skip PostToolUse normalization for the replacment - 
                    # its already a structured error and shouldn't be reshaped. 
                
                else: 
                    # Hook allowed the call. Dispatch to the implementation.
                    if tool_name not in TOOL_IMPLEMENTATIONS:
                        result = {
                            "isError": True,
                            "errorCategory": "validation",
                            "isRetryable": False,
                            "message": f"Unknown tool: {tool_name}",
                        }
                    else:
                        try:
                            result = TOOL_IMPLEMENTATIONS[tool_name](**tool_input)
                        except Exception as exc:
                            # Catch-all: turn any unexpected exception into a
                            # transient error so the agent can decide what to do.
                            result = {
                                "isError": True,
                                "errorCategory": "transient",
                                "isRetryable": True,
                                "message": "Tool raised an unexpected exception.",
                                "detail": str(exc),
                            }

                    # === PostToolUse hook ===
                    result = post_tool_use_hook(tool_name, result)

                    # === Session state update ===
                    update_session_from_result(tool_name, result, session)
                
                run.tool_calls.append({
                    "name": tool_name,
                    "input": tool_input,
                    "result": result,
                    "blocked_by_gate": not allow, #observability
                })

                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tool_use_id,
                    "content": json.dumps(result),
                    "is_error": result.get("isError", False),
                })

            # Append all tool results as a single user-role message.
            # This is the contract: tool results live in a user message
            # under content blocks of type "tool_result". The model sees
            # them on its next turn and reasons about the next action.
            messages.append({"role": "user", "content": tool_results})

            # Loop back — the model will see the new results and decide
            # whether to call more tools or produce a final answer.
            continue

        # Any other stop_reason ("max_tokens", "stop_sequence", etc.) is
        # treated as termination. In practice you'd add specific handling
        # for "max_tokens" (e.g., warn the user the response was truncated).
        run.final_text = _extract_text(response.content)
        break

    # Surface gate violations on the run summary for observability
    run.gate_violations = list(session.gate_violations)
    return run, messages, session


def _extract_text(content_blocks: list[Any]) -> str:
    """Pull text-only blocks out of an assistant response."""
    parts = []
    for block in content_blocks:
        if getattr(block, "type", None) == "text":
            parts.append(block.text)
    return "\n".join(parts).strip()