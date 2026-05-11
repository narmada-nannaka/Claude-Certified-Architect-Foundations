"""Dry-run tool routing test.

We don't need the full agent loop to validate that our tool descriptions
are unambiguous. A single Claude API call with our tool definitions and
ambiguous user prompts will reveal misrouting before we wire up hooks
and loops.

This is the cheapest possible feedback loop on Domain 2, Task Statement 2.1.
"""
import json
import os
from pathlib import Path
import sys

from anthropic import Anthropic
from dotenv import load_dotenv

# Allow importing src/ from the scenario root
sys.path.insert(0, str(Path(__file__).parent.parent))

load_dotenv()
client = Anthropic()

# Pull tool schemas straight from the MCP server module so the test
# always stays in sync with the source of truth.
from src.mcp_server import get_customer, lookup_order, process_refund, escalate_to_human

# Convert to Claude's tool-use schema format.
# In a real setup the Agent SDK does this for you; here we do it manually
# for the sanity check.
TOOLS = [
    {
        "name": "get_customer",
        "description": get_customer.__doc__,
        "input_schema": {
            "type": "object",
            "properties": {
                "customer_id": {"type": "string", "description": "Format C-NNNN"},
                "email": {"type": "string", "description": "Full email address"},
            },
        },
    },
    {
        "name": "lookup_order",
        "description": lookup_order.__doc__,
        "input_schema": {
            "type": "object",
            "properties": {
                "order_id": {"type": "string", "description": "Format O-NNNN"},
            },
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
            "required": ["summary", "root_cause", "recommended_action"],
        },
    },
]

# Prompts designed to probe routing.
# Each has an expected first-tool-call to check against.
TEST_PROMPTS = [
    {
        "user_message": "Hi, can you check on my order O-5001?",
        "expected_first_tool": "get_customer",  # must verify identity first
        "reason": "Tool descriptions say get_customer must run FIRST",
    },
    {
        "user_message": "My customer ID is C-1001 and I want to know what I ordered last month.",
        "expected_first_tool": "get_customer",
        "reason": "Customer ID provided — verify before looking up orders",
    },
    {
        "user_message": "I'm Ada Lovelace, [email protected]. I need a refund on O-5001 for $249.99 because it arrived broken.",
        "expected_first_tool": "get_customer",
        "reason": "Even with full info, identity verification gates everything",
    },
    {
        "user_message": "I want to talk to a real person, this is ridiculous.",
        "expected_first_tool": "escalate_to_human",
        "reason": "Explicit human request — honor immediately (Task 5.2)",
    },
]


def run_routing_check():
    passed = 0
    failed = 0
    for i, case in enumerate(TEST_PROMPTS, 1):
        print(f"\n--- Test {i}: {case['user_message'][:60]}... ---")
        print(f"  Expecting first tool: {case['expected_first_tool']}")
        print(f"  Reason: {case['reason']}")

        response = client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=1024,
            tools=TOOLS,
            messages=[{"role": "user", "content": case["user_message"]}],
            system=(
                "You are a customer support agent. "
                "ALWAYS call get_customer as your FIRST tool call in any session "
                "that involves orders or account lookups — even before asking the "
                "customer for their ID. If the customer has not provided an ID, "
                "call get_customer with no arguments; the error response will tell "
                "you what credentials to request. "
                "When a customer explicitly asks for a human agent, immediately call "
                "escalate_to_human with whatever context is available — do not respond "
                "with plain text first."
            ),
        )

        # Find the first tool_use block
        first_tool = None
        for block in response.content:
            if block.type == "tool_use":
                first_tool = block.name
                break

        if first_tool == case["expected_first_tool"]:
            print(f"  [PASS] -- chose {first_tool}")
            passed += 1
        else:
            print(f"  [FAIL] -- chose {first_tool} (expected {case['expected_first_tool']})")
            failed += 1

        print(f"  stop_reason: {response.stop_reason}")

    print(f"\n=== Routing check: {passed} passed, {failed} failed ===")
    return failed == 0


if __name__ == "__main__":
    success = run_routing_check()
    sys.exit(0 if success else 1)