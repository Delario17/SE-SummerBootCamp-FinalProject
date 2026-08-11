"""Tests for feedback parser."""
import pytest
from src.models import ToolResult, Feedback, FeedbackType
from src.feedback.parser import FeedbackParser


class TestFeedbackParser:
    def test_parse_pytest_all_pass(self):
        tr = ToolResult(
            tool_call_id="c1", tool_name="run_shell",
            success=True,
            stdout="tests/test_main.py::test_add PASSED\n======= 3 passed in 0.5s =======",
            stderr="", exit_code=0, duration_ms=500,
        )
        fb = FeedbackParser.parse(tr)
        assert fb.type == FeedbackType.UNKNOWN  # no failure, type is UNKNOWN
        assert fb.passed_count == 3
        assert fb.failed_count == 0

    def test_parse_pytest_failure(self):
        tr = ToolResult(
            tool_call_id="c1", tool_name="run_shell",
            success=False,
            stdout=(
                "tests/test_main.py::test_add PASSED\n"
                "tests/test_main.py::test_sub FAILED\n"
                "AssertionError: assert 3 == 5\n"
                "======= 1 failed, 2 passed in 0.5s ======="
            ),
            stderr="", exit_code=1, duration_ms=500,
        )
        fb = FeedbackParser.parse(tr)
        assert fb.type == FeedbackType.ASSERTION_FAILURE
        assert fb.failed_count == 1
        assert fb.passed_count == 2
        assert "test_sub" in fb.detail

    def test_parse_pytest_syntax_error(self):
        tr = ToolResult(
            tool_call_id="c1", tool_name="run_shell",
            success=False,
            stdout="SyntaxError: invalid syntax\n  File 'test.py', line 5\n    x =",
            stderr="", exit_code=1, duration_ms=100,
        )
        fb = FeedbackParser.parse(tr)
        assert fb.type == FeedbackType.SYNTAX_ERROR
        assert "SyntaxError" in fb.detail

    def test_parse_pytest_import_error(self):
        tr = ToolResult(
            tool_call_id="c1", tool_name="run_shell",
            success=False,
            stdout="ImportError: No module named 'nonexistent'\nModuleNotFoundError",
            stderr="", exit_code=1, duration_ms=100,
        )
        fb = FeedbackParser.parse(tr)
        assert fb.type == FeedbackType.IMPORT_ERROR

    def test_parse_timeout(self):
        tr = ToolResult(
            tool_call_id="c1", tool_name="run_shell",
            success=False,
            stdout="",
            stderr="Command timed out after 60s: pytest tests/",
            exit_code=-1, duration_ms=60000,
        )
        fb = FeedbackParser.parse(tr)
        assert fb.type == FeedbackType.TIMEOUT

    def test_parse_unknown_error(self):
        tr = ToolResult(
            tool_call_id="c1", tool_name="run_shell",
            success=False,
            stdout="Some random error",
            stderr="more error details",
            exit_code=255, duration_ms=100,
        )
        fb = FeedbackParser.parse(tr)
        assert fb.type == FeedbackType.UNKNOWN

    def test_parse_success_no_tests(self):
        tr = ToolResult(
            tool_call_id="c1", tool_name="run_shell",
            success=True,
            stdout="hello world",
            stderr="", exit_code=0, duration_ms=10,
        )
        fb = FeedbackParser.parse(tr)
        assert fb.type == FeedbackType.UNKNOWN
        assert fb.summary == "Command executed successfully"

    def test_to_message(self):
        fb = Feedback(
            type=FeedbackType.ASSERTION_FAILURE,
            summary="1 test failed",
            detail="test_sub: assert 3 == 5",
            suggestion="Check the subtraction logic",
            failed_count=1,
            passed_count=2,
        )
        msg = FeedbackParser.to_message(fb)
        assert "FAILED" in msg
        assert "test_sub" in msg
        assert "1 failed" in msg