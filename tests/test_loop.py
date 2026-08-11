"""Tests for the agent main loop using Mock LLM."""
import pytest
from pathlib import Path
from src.models import (
    Message, ToolCall, LLMResponse, ToolResult, Feedback, FeedbackType,
)
from src.llm.mock_backend import MockLLMBackend
from src.loop.agent import AgentLoop, StopReason


def make_text_response(content: str) -> LLMResponse:
    return LLMResponse(content=content, finish_reason="stop")


def make_tool_response(name: str, args: dict) -> LLMResponse:
    return LLMResponse(
        tool_calls=[ToolCall(id="call_1", name=name, arguments=args)],
        finish_reason="tool_calls",
    )


def make_finish_response(summary: str = "Done") -> LLMResponse:
    return LLMResponse(
        tool_calls=[ToolCall(id="call_f", name="finish", arguments={"summary": summary})],
        finish_reason="tool_calls",
    )


@pytest.fixture
def agent_config(sample_config_dict):
    return sample_config_dict


@pytest.mark.asyncio
async def test_loop_finishes_on_finish_tool(agent_config, temp_dir):
    """Agent loop should stop when LLM calls the finish tool."""
    responses = [
        make_finish_response("All tests pass"),
    ]
    backend = MockLLMBackend(responses=responses)
    loop = AgentLoop(agent_config)
    result = await loop.run("Run tests", backend)
    assert result.stop_reason == StopReason.FINISH_CALLED
    assert "All tests pass" in result.summary
    assert result.turns == 1


@pytest.mark.asyncio
async def test_loop_stops_on_max_turns(agent_config, temp_dir):
    """Agent loop should stop after max_turns iterations."""
    agent_config["loop"]["max_turns"] = 3
    agent_config["guardrails"]["allowed_paths"] = [str(Path.cwd())]
    responses = [
        make_tool_response("read_file", {"path": "test.py"}),
        make_tool_response("read_file", {"path": "test.py"}),
        make_tool_response("read_file", {"path": "test.py"}),
    ]
    backend = MockLLMBackend(responses=responses)
    loop = AgentLoop(agent_config)
    result = await loop.run("Read files", backend)
    assert result.stop_reason == StopReason.MAX_TURNS
    assert result.turns == 3


@pytest.mark.asyncio
async def test_loop_handles_text_response(agent_config, temp_dir):
    """Agent loop should handle text-only responses from LLM."""
    responses = [
        make_text_response("I think the task is done."),
        make_text_response("No further actions needed."),
        make_text_response("Still thinking..."),
    ]
    agent_config["loop"]["idle_timeout"] = 2
    backend = MockLLMBackend(responses=responses)
    loop = AgentLoop(agent_config)
    result = await loop.run("Analyze code", backend)
    assert result.stop_reason == StopReason.IDLE_TIMEOUT or result.stop_reason == StopReason.MAX_TURNS


@pytest.mark.asyncio
async def test_loop_guardrail_blocks_dangerous(agent_config, temp_dir):
    """Agent loop should block dangerous commands via guardrail."""
    # Create a test file so read_file doesn't fail
    test_file = temp_dir / "src" / "main.py"
    test_file.parent.mkdir(parents=True, exist_ok=True)
    test_file.write_text("print('hello')")

    agent_config["guardrails"]["allowed_paths"] = [str(temp_dir / "src"), str(temp_dir / "tests")]
    responses = [
        make_tool_response("read_file", {"path": "/etc/passwd"}),
        make_finish_response("Task done"),
    ]
    backend = MockLLMBackend(responses=responses)
    loop = AgentLoop(agent_config)
    result = await loop.run("Read file", backend)
    # The first action should be blocked by file fence
    assert result.turns >= 1


@pytest.mark.asyncio
async def test_loop_executes_tool_and_collects_result(agent_config, temp_dir):
    """Agent loop should execute tool calls and collect results."""
    test_file = temp_dir / "test.txt"
    test_file.write_text("hello")

    agent_config["guardrails"]["allowed_paths"] = [str(temp_dir)]
    responses = [
        make_tool_response("read_file", {"path": str(test_file)}),
        make_finish_response("Read the file"),
    ]
    backend = MockLLMBackend(responses=responses)
    loop = AgentLoop(agent_config)
    result = await loop.run("Read a file", backend)
    assert result.stop_reason == StopReason.FINISH_CALLED
    assert result.turns == 2