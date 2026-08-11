# tests/test_integration.py
"""Integration tests — full harness operation with Mock LLM."""
import pytest
from pathlib import Path
from src.models import Message, ToolCall, LLMResponse
from src.llm.mock_backend import MockLLMBackend
from src.loop.agent import AgentLoop, StopReason


def make_response(tool_calls=None, content=None):
    return LLMResponse(
        content=content,
        tool_calls=tool_calls,
        finish_reason="tool_calls" if tool_calls else "stop",
    )


@pytest.fixture
def harness_config(temp_dir):
    return {
        "loop": {"max_turns": 10, "idle_timeout": 3},
        "llm": {
            "provider": "openai_compat", "model": "gpt-4o",
            "api_base": "", "api_key_cmd": "echo test",
            "temperature": 0.1, "max_tokens": 4096,
        },
        "tools": {
            "allowed": ["read_file", "write_file", "run_shell", "finish"],
            "shell_timeout": 60,
        },
        "guardrails": {
            "allowed_paths": [str(temp_dir)],
            "command_rules": [
                {"pattern": r"^(ls|cat|pytest|echo|python|mkdir)\b", "level": "safe"},
                {"pattern": r"\brm -rf\b", "level": "dangerous"},
            ],
            "hitl": {"timeout": 30, "enabled": True},
            "sandbox": {"enabled": False, "memory_limit_mb": 512, "cpu_time_limit": 30},
        },
        "memory": {"db_path": ":memory:", "max_context_turns": 10},
        "web": {"host": "0.0.0.0", "port": 8080},
    }


@pytest.mark.asyncio
async def test_full_cycle_write_and_read(harness_config, temp_dir):
    """Agent writes a file, then reads it back."""
    test_file = temp_dir / "output.txt"
    responses = [
        make_response(tool_calls=[
            ToolCall(id="c1", name="write_file", arguments={
                "path": str(test_file), "content": "hello world",
            }),
        ]),
        make_response(tool_calls=[
            ToolCall(id="c2", name="read_file", arguments={
                "path": str(test_file),
            }),
        ]),
        make_response(tool_calls=[
            ToolCall(id="c3", name="finish", arguments={
                "summary": "File written and verified",
            }),
        ]),
    ]
    backend = MockLLMBackend(responses=responses)
    loop = AgentLoop(harness_config)
    result = await loop.run("Write and read a file", backend)
    assert result.stop_reason == StopReason.FINISH_CALLED
    assert "File written" in result.summary
    assert Path(test_file).read_text() == "hello world"


@pytest.mark.asyncio
async def test_guardrail_blocks_and_continues(harness_config, temp_dir):
    """Guardrail blocks a dangerous action, agent continues with safe action."""
    test_file = temp_dir / "safe.txt"
    test_file.write_text("safe content")
    responses = [
        # Attempt 1: dangerous command (blocked)
        make_response(tool_calls=[
            ToolCall(id="c1", name="run_shell", arguments={"cmd": "rm -rf /"}),
        ]),
        # Attempt 2: safe command (passes)
        make_response(tool_calls=[
            ToolCall(id="c2", name="read_file", arguments={"path": str(test_file)}),
        ]),
        # Finish
        make_response(tool_calls=[
            ToolCall(id="c3", name="finish", arguments={"summary": "Done"}),
        ]),
    ]
    backend = MockLLMBackend(responses=responses)
    loop = AgentLoop(harness_config)
    result = await loop.run("Do something", backend)
    assert result.stop_reason == StopReason.FINISH_CALLED


@pytest.mark.asyncio
async def test_feedback_loop_after_failure(harness_config, temp_dir):
    """Agent runs a failing test, then retries."""
    test_file = temp_dir / "test_fail.py"
    test_file.write_text("def test_fail(): assert 1 == 2")
    responses = [
        make_response(tool_calls=[
            ToolCall(id="c1", name="run_shell", arguments={
                "cmd": f"cd {temp_dir} && python -m pytest test_fail.py -v",
            }),
        ]),
        make_response(tool_calls=[
            ToolCall(id="c2", name="write_file", arguments={
                "path": str(test_file), "content": "def test_fail(): assert 1 == 1",
            }),
        ]),
        make_response(tool_calls=[
            ToolCall(id="c3", name="finish", arguments={"summary": "Fixed test"}),
        ]),
    ]
    backend = MockLLMBackend(responses=responses)
    loop = AgentLoop(harness_config)
    result = await loop.run("Fix failing test", backend)
    assert result.stop_reason == StopReason.FINISH_CALLED
    assert "Fixed" in result.summary


@pytest.mark.asyncio
async def test_max_turns_stops_loop(harness_config, temp_dir):
    """Loop stops after max_turns reached."""
    harness_config["loop"]["max_turns"] = 2
    responses = [
        make_response(tool_calls=[
            ToolCall(id=f"c{i}", name="run_shell", arguments={"cmd": "echo hello"})
        ]) for i in range(5)
    ]
    backend = MockLLMBackend(responses=responses)
    loop = AgentLoop(harness_config)
    result = await loop.run("Infinite loop prevention", backend)
    assert result.stop_reason == StopReason.MAX_TURNS
    assert result.turns == 2