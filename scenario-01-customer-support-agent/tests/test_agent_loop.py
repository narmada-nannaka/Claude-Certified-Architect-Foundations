"""Tests for agentic loop control flow.

These tests focus on loop mechanics, not on what the model decides to do.
That's deliberate: the model's decisions vary across runs, but the loop's
control flow must be deterministic.
"""
import pytest
from unittest.mock import MagicMock, patch

from src.agent import run_agent, AgentRun


def _mock_response(stop_reason: str, content_blocks: list):
    """Build a fake API response object."""
    response = MagicMock()
    response.stop_reason = stop_reason
    response.content = content_blocks
    return response


def _text_block(text: str):
    block = MagicMock()
    block.type = "text"
    block.text = text
    return block


def _tool_use_block(tool_id: str, name: str, input_data: dict):
    block = MagicMock()
    block.type = "tool_use"
    block.id = tool_id
    block.name = name
    block.input = input_data
    return block


def test_loop_terminates_on_end_turn():
    """Task 1.1: stop_reason='end_turn' is the termination signal."""
    with patch("src.agent.Anthropic") as MockAnthropic:
        client = MockAnthropic.return_value
        client.messages.create.return_value = _mock_response(
            stop_reason="end_turn",
            content_blocks=[_text_block("Hello! How can I help?")],
        )

        run, _ = run_agent("Hi there")

        assert run.stop_reason == "end_turn"
        assert run.iterations == 1
        assert run.final_text == "Hello! How can I help?"
        assert run.tool_calls == []


def test_loop_continues_on_tool_use_then_terminates():
    """Task 1.1: stop_reason='tool_use' continues the loop; results
    are appended; the next end_turn terminates."""
    with patch("src.agent.Anthropic") as MockAnthropic:
        client = MockAnthropic.return_value

        # First call: model asks for get_customer
        first_response = _mock_response(
            stop_reason="tool_use",
            content_blocks=[_tool_use_block("tu_1", "get_customer", {"customer_id": "C-1001"})],
        )
        # Second call: model is done
        second_response = _mock_response(
            stop_reason="end_turn",
            content_blocks=[_text_block("Verified Ada Lovelace.")],
        )

        client.messages.create.side_effect = [first_response, second_response]

        run, history = run_agent("I'm C-1001")

        assert run.iterations == 2
        assert len(run.tool_calls) == 1
        assert run.tool_calls[0]["name"] == "get_customer"
        assert run.tool_calls[0]["result"]["verified"] is True
        assert run.final_text == "Verified Ada Lovelace."

        # History should contain: user msg, assistant tool_use,
        # user tool_result, assistant final text
        assert len(history) == 4
        assert history[0]["role"] == "user"
        assert history[1]["role"] == "assistant"
        assert history[2]["role"] == "user"  # tool_result lives in user role
        assert history[3]["role"] == "assistant"


def test_loop_handles_unknown_tool_gracefully():
    """A model hallucinated tool name shouldn't crash the loop."""
    with patch("src.agent.Anthropic") as MockAnthropic:
        client = MockAnthropic.return_value

        client.messages.create.side_effect = [
            _mock_response(
                stop_reason="tool_use",
                content_blocks=[_tool_use_block("tu_1", "delete_universe", {})],
            ),
            _mock_response(
                stop_reason="end_turn",
                content_blocks=[_text_block("Sorry, I can't do that.")],
            ),
        ]

        run, _ = run_agent("Do the thing")

        # The error result was reported back to the model, which then
        # produced a graceful end_turn response.
        assert run.iterations == 2
        assert run.tool_calls[0]["result"]["isError"] is True
        assert run.stop_reason == "end_turn"


def test_safety_cap_engages_only_in_runaway_scenarios():
    """The cap is a circuit breaker, NOT the primary stop. It should
    not trip on normal conversations."""
    with patch("src.agent.Anthropic") as MockAnthropic:
        client = MockAnthropic.return_value

        # Simulate a model that never says end_turn — infinite tool calls.
        infinite_tool_response = _mock_response(
            stop_reason="tool_use",
            content_blocks=[_tool_use_block("tu_x", "get_customer", {"customer_id": "C-1001"})],
        )
        client.messages.create.return_value = infinite_tool_response

        run, _ = run_agent("Trigger infinite loop")

        # The cap engaged, but did so AFTER many iterations.
        # If iterations == 1 or 2, the cap is incorrectly the primary stop.
        assert run.hit_safety_cap is True
        assert run.iterations > 20  # Well past any reasonable conversation


def test_parallel_tool_calls_in_single_response_are_all_executed():
    """A single response can contain multiple tool_use blocks.
    Skill in Task 1.3: 'Spawning parallel subagents by emitting multiple
    Task tool calls in a single coordinator response.' Same mechanism."""
    with patch("src.agent.Anthropic") as MockAnthropic:
        client = MockAnthropic.return_value

        client.messages.create.side_effect = [
            _mock_response(
                stop_reason="tool_use",
                content_blocks=[
                    _tool_use_block("tu_1", "lookup_order", {"order_id": "O-5001"}),
                    _tool_use_block("tu_2", "lookup_order", {"order_id": "O-5002"}),
                ],
            ),
            _mock_response(
                stop_reason="end_turn",
                content_blocks=[_text_block("Both orders look fine.")],
            ),
        ]

        run, _ = run_agent("Check both my recent orders")

        assert run.iterations == 2
        assert len(run.tool_calls) == 2
        assert run.tool_calls[0]["name"] == "lookup_order"
        assert run.tool_calls[1]["name"] == "lookup_order"