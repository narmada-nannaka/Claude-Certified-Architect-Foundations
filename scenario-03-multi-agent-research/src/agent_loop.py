"""Reusable agent loop with stop_reason control flow.

This is the same architectural pattern as Scenario 1's run_agent: send
to Claude API, inspect stop_reason, execute tools, append results,
repeat until end_turn.

The differences are surface-level — we accept tool schemas, tool
implementations, and system prompt as parameters so the same loop
can serve different agents (coordinator, future subagents).
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Callable

from anthropic import Anthropic


MAX_ITERATIONS_SAFETY_CAP = 25


@dataclass
class AgentRun:
    """One agent run's observable outcome.

    Used by tests and by the coordinator to inspect what happened
    during a subagent dispatch.
    """
    final_text: str = ""
    iterations: int = 0
    tool_calls: list[dict] = field(default_factory=list)
    stop_reason: str = ""
    hit_safety_cap: bool = False


def run_agent_loop(
    user_message: str,
    system_prompt: str,
    tool_schemas: list[dict],
    tool_implementations: dict[str, Callable],
    model: str = "claude-sonnet-4-6",
    conversation_history: list[dict] | None = None,
) -> tuple[AgentRun, list[dict]]:
    """Run an agent loop until stop_reason == 'end_turn'.

    Args:
        user_message: the new user input.
        system_prompt: the agent's system prompt.
        tool_schemas: Claude API tool definitions.
        tool_implementations: dict of tool_name → callable.
        model: Claude model identifier.
        conversation_history: prior messages (default empty).

    Returns:
        (AgentRun summary, updated conversation_history).
    """
    client = Anthropic()
    messages = list(conversation_history or [])
    messages.append({"role": "user", "content": user_message})

    run = AgentRun()

    while True:
        run.iterations += 1

        if run.iterations > MAX_ITERATIONS_SAFETY_CAP:
            run.hit_safety_cap = True
            run.final_text = "[Safety cap reached.]"
            break

        response = client.messages.create(
            model=model,
            max_tokens=4096,
            system=system_prompt,
            tools=tool_schemas,
            messages=messages,
        )

        run.stop_reason = response.stop_reason
        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason == "end_turn":
            run.final_text = _extract_text(response.content)
            break

        if response.stop_reason == "tool_use":
            tool_results = []
            for block in response.content:
                if block.type != "tool_use":
                    continue

                tool_name = block.name
                tool_input = block.input
                tool_use_id = block.id

                if tool_name not in tool_implementations:
                    result = {
                        "isError": True,
                        "errorCategory": "validation",
                        "isRetryable": False,
                        "message": f"Unknown tool: {tool_name}",
                    }
                else:
                    try:
                        result = tool_implementations[tool_name](tool_input)
                    except Exception as exc:
                        result = {
                            "isError": True,
                            "errorCategory": "transient",
                            "isRetryable": True,
                            "message": "Tool raised an unexpected exception.",
                            "detail": str(exc),
                        }

                run.tool_calls.append({
                    "name": tool_name,
                    "input": tool_input,
                    "result": result,
                })

                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tool_use_id,
                    "content": json.dumps(result),
                    "is_error": result.get("isError", False),
                })

            messages.append({"role": "user", "content": tool_results})
            continue

        run.final_text = _extract_text(response.content)
        break

    return run, messages


def _extract_text(content_blocks: list[Any]) -> str:
    parts = []
    for block in content_blocks:
        if getattr(block, "type", None) == "text":
            parts.append(block.text)
    return "\n".join(parts).strip()