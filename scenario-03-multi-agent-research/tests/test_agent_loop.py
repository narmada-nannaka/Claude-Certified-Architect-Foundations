"""Tests for the reusable agent loop.

We mock the Claude API and verify the loop:
- Terminates on end_turn
- Continues on tool_use
- Handles parallel tool_use blocks (the key Task 1.3 mechanism)
- Treats Task tool calls identically to other tool calls
"""
from unittest.mock import MagicMock, patch

from src.agent_loop import run_agent_loop


def _mock_response(stop_reason: str, content_blocks: list):
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
    with patch("src.agent_loop.Anthropic") as MockAnthropic:
        client = MockAnthropic.return_value
        client.messages.create.return_value = _mock_response(
            stop_reason="end_turn",
            content_blocks=[_text_block("Done.")],
        )

        run, _ = run_agent_loop(
            user_message="hi",
            system_prompt="test",
            tool_schemas=[],
            tool_implementations={},
        )

        assert run.stop_reason == "end_turn"
        assert run.iterations == 1


def test_parallel_task_calls_all_execute():
    """Sample Question 7's mechanism: coordinator emits multiple Task
    calls in one response. The loop must execute all of them."""
    captured_calls = []

    def fake_task(input_data):
        captured_calls.append(input_data)
        return {"subagent": input_data["agent_name"], "findings_count": 0, "findings": []}

    with patch("src.agent_loop.Anthropic") as MockAnthropic:
        client = MockAnthropic.return_value
        client.messages.create.side_effect = [
            _mock_response(
                stop_reason="tool_use",
                content_blocks=[
                    _tool_use_block("t1", "Task", {"agent_name": "web_research", "prompt": "music"}),
                    _tool_use_block("t2", "Task", {"agent_name": "web_research", "prompt": "film"}),
                    _tool_use_block("t3", "Task", {"agent_name": "document_analysis", "prompt": "writing"}),
                ],
            ),
            _mock_response(stop_reason="end_turn", content_blocks=[_text_block("done")]),
        ]

        run, _ = run_agent_loop(
            user_message="research creative industries",
            system_prompt="test",
            tool_schemas=[],
            tool_implementations={"Task": fake_task},
        )

        # Three Task calls dispatched in one iteration
        assert len(captured_calls) == 3
        assert captured_calls[0]["prompt"] == "music"
        assert captured_calls[1]["prompt"] == "film"
        assert captured_calls[2]["prompt"] == "writing"
        # Loop completed in 2 iterations (one tool batch + one end_turn)
        assert run.iterations == 2


def test_unknown_tool_is_handled_gracefully():
    with patch("src.agent_loop.Anthropic") as MockAnthropic:
        client = MockAnthropic.return_value
        client.messages.create.side_effect = [
            _mock_response(
                stop_reason="tool_use",
                content_blocks=[_tool_use_block("tx", "delete_universe", {})],
            ),
            _mock_response(stop_reason="end_turn", content_blocks=[_text_block("can't do that")]),
        ]

        run, _ = run_agent_loop(
            user_message="trigger",
            system_prompt="test",
            tool_schemas=[],
            tool_implementations={},
        )

        assert run.tool_calls[0]["result"]["isError"] is True
        assert run.stop_reason == "end_turn"


def test_safety_cap_engages_on_runaway():
    infinite = _mock_response(
        stop_reason="tool_use",
        content_blocks=[_tool_use_block("t", "Task", {"agent_name": "web_research", "prompt": "x"})],
    )

    def fake_task(input_data):
        return {"subagent": "web_research", "findings": []}

    with patch("src.agent_loop.Anthropic") as MockAnthropic:
        client = MockAnthropic.return_value
        client.messages.create.return_value = infinite

        run, _ = run_agent_loop(
            user_message="loop forever",
            system_prompt="test",
            tool_schemas=[],
            tool_implementations={"Task": fake_task},
        )

        assert run.hit_safety_cap is True
        assert run.iterations > 20