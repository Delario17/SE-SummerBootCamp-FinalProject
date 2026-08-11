"""Tests for data models."""
from dataclasses import asdict
from src.models import (
    Message, ToolCall, ToolResult, GuardrailResult,
    Feedback, FeedbackType, LLMResponse, Session, Action, CommandLevel,
)


def test_message_creation():
    msg = Message(role="user", content="hello")
    assert msg.role == "user"
    assert msg.content == "hello"
    assert msg.tool_calls is None


def test_message_with_tool_calls():
    tc = ToolCall(id="call_1", name="read_file", arguments={"path": "test.py"})
    msg = Message(role="assistant", content=None, tool_calls=[tc])
    assert msg.tool_calls[0].name == "read_file"


def test_tool_result_fields():
    result = ToolResult(
        tool_call_id="call_1",
        tool_name="read_file",
        success=True,
        stdout="file content",
        stderr="",
        exit_code=0,
        duration_ms=12.5,
    )
    assert result.success is True
    assert result.exit_code == 0


def test_guardrail_result_blocked():
    result = GuardrailResult(
        allowed=False, level="dangerous",
        reason="rm -rf is forbidden", requires_hitl=True, blocked=True,
    )
    assert result.blocked is True
    assert result.allowed is False


def test_guardrail_result_allowed():
    result = GuardrailResult(
        allowed=True, level="safe",
        reason=None, requires_hitl=False, blocked=False,
    )
    assert result.blocked is False


def test_feedback_types():
    assert FeedbackType.SYNTAX_ERROR.value == "SYNTAX_ERROR"
    assert FeedbackType.ASSERTION_FAILURE.value == "ASSERTION_FAILURE"
    assert FeedbackType.IMPORT_ERROR.value == "IMPORT_ERROR"
    assert FeedbackType.TIMEOUT.value == "TIMEOUT"
    assert FeedbackType.UNKNOWN.value == "UNKNOWN"


def test_feedback_creation():
    fb = Feedback(
        type=FeedbackType.ASSERTION_FAILURE,
        summary="test_add failed",
        detail="assert 3 == 5 in test_add",
        suggestion="Check the addition logic",
        failed_count=1,
        passed_count=2,
    )
    assert fb.type == FeedbackType.ASSERTION_FAILURE
    assert fb.failed_count == 1


def test_llm_response_with_tool_calls():
    tc = ToolCall(id="call_1", name="run_shell", arguments={"cmd": "pytest"})
    resp = LLMResponse(
        content=None,
        tool_calls=[tc],
        finish_reason="tool_calls",
        usage={"prompt_tokens": 100, "completion_tokens": 50},
    )
    assert resp.finish_reason == "tool_calls"
    assert len(resp.tool_calls) == 1


def test_llm_response_text():
    resp = LLMResponse(
        content="Task completed.",
        tool_calls=None,
        finish_reason="stop",
        usage=None,
    )
    assert resp.content == "Task completed."


def test_action_creation():
    action = Action(
        tool_name="run_shell",
        arguments={"cmd": "rm -rf /"},
    )
    assert action.tool_name == "run_shell"
    assert action.arguments["cmd"] == "rm -rf /"


def test_command_level_enum():
    assert CommandLevel.SAFE.value == "safe"
    assert CommandLevel.WARN.value == "warn"
    assert CommandLevel.DANGEROUS.value == "dangerous"


def test_session_fields():
    from datetime import datetime
    session = Session(
        id="abc-123",
        task="Run tests",
        status="running",
        turns=0,
        created_at=datetime.now(),
        completed_at=None,
    )
    assert session.status == "running"
    assert session.turns == 0