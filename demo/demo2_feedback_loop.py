#!/usr/bin/env python3
"""Demo 2: Feedback loop receives failure and changes next action.

This demo shows the feedback loop parsing a test failure and injecting
structured feedback that the LLM can use to self-correct.
Uses Mock LLM with a pre-defined sequence of responses.
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.models import Message, ToolCall, LLMResponse, ToolResult
from src.llm.mock_backend import MockLLMBackend
from src.feedback.parser import FeedbackParser
from src.loop.agent import AgentLoop


async def main():
    print("=" * 60)
    print("Demo 2: Feedback Loop Drives Self-Correction")
    print("=" * 60)

    # Test 1: Parse pytest failure
    print("\n[Test 1] FeedbackParser parses pytest failure:")
    tr = ToolResult(
        tool_call_id="c1", tool_name="run_shell",
        success=False,
        stdout=(
            "tests/test_calc.py::test_add FAILED\n"
            "AssertionError: assert 3 == 5\n"
            "======= 1 failed, 2 passed in 0.5s ======="
        ),
        stderr="", exit_code=1, duration_ms=500,
    )
    fb = FeedbackParser.parse(tr)
    print(f"  Type: {fb.type.value}")
    print(f"  Failed: {fb.failed_count}, Passed: {fb.passed_count}")
    print(f"  Detail: {fb.detail}")
    assert fb.type.value == "ASSERTION_FAILURE", "FAIL: Should detect assertion failure!"
    assert fb.failed_count == 1, "FAIL: Should count 1 failure!"
    print("  PASS")

    # Test 2: FeedbackParser generates suggestion
    print("\n[Test 2] FeedbackParser generates suggestion for each failure type:")
    from src.models import FeedbackType
    for ft in FeedbackType:
        tr = ToolResult(
            tool_call_id="c1", tool_name="run_shell",
            success=False,
            stdout=f"{ft.value} error occurred",
            stderr="", exit_code=1, duration_ms=100,
        )
        fb = FeedbackParser.parse(tr)
        assert fb.suggestion != "", f"FAIL: No suggestion for {ft.value}!"
        print(f"  {ft.value}: {fb.suggestion}")
    print("  PASS")

    # Test 3: Feedback message is formatted for LLM
    print("\n[Test 3] Feedback formatted as LLM context message:")
    fb = FeedbackParser.parse(tr)
    msg = FeedbackParser.to_message(fb)
    print(f"  {msg[:100]}...")
    assert "[FEEDBACK]" in msg, "FAIL: Feedback message missing [FEEDBACK] tag!"
    print("  PASS")

    # Test 4: Mock LLM loop with failure injection
    print("\n[Test 4] Mock LLM loop handles failure and retries:")
    config = {
        "loop": {"max_turns": 5, "idle_timeout": 3},
        "llm": {"provider": "openai_compat", "model": "gpt-4o", "api_base": "", "api_key_cmd": "", "temperature": 0.1, "max_tokens": 4096},
        "tools": {"allowed": ["read_file", "write_file", "run_shell", "finish"], "shell_timeout": 60},
        "guardrails": {"allowed_paths": ["./"], "command_rules": [], "hitl": {"timeout": 30, "enabled": False}, "sandbox": {"enabled": False}},
        "memory": {"db_path": ":memory:", "max_context_turns": 10},
        "web": {"host": "0.0.0.0", "port": 8080},
    }
    responses = [
        LLMResponse(
            tool_calls=[ToolCall(id="c1", name="run_shell", arguments={"cmd": "pytest"})],
            finish_reason="tool_calls",
        ),
        LLMResponse(
            tool_calls=[ToolCall(id="c2", name="finish", arguments={"summary": "Fixed the test"})],
            finish_reason="tool_calls",
        ),
    ]
    backend = MockLLMBackend(responses=responses)
    loop = AgentLoop(config)
    result = await loop.run("Fix failing tests", backend)
    print(f"  Stop reason: {result.stop_reason.value}")
    print(f"  Turns: {result.turns}")
    print(f"  Summary: {result.summary}")
    assert result.turns == 2, "FAIL: Should complete in 2 turns!"
    print("  PASS")

    print("\n" + "=" * 60)
    print("Demo 2: ALL TESTS PASSED")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())