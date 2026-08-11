"""Feedback parser — extracts structured feedback from tool execution results."""
import re
from src.models import ToolResult, Feedback, FeedbackType


class FeedbackParser:
    """Parses tool execution output into structured feedback."""

    @staticmethod
    def parse(tool_result: ToolResult) -> Feedback:
        """Parse a ToolResult into a Feedback object.

        Detects pytest output, syntax errors, import errors, and timeouts.
        """
        stdout = tool_result.stdout
        stderr = tool_result.stderr
        combined = f"{stdout}\n{stderr}"

        # Check for timeout first
        if "timeout" in combined.lower() or "timed out" in combined.lower():
            return Feedback(
                type=FeedbackType.TIMEOUT,
                summary="Command timed out",
                detail=combined[:500],
                suggestion="Consider optimizing the command or increasing the timeout.",
                failed_count=0,
                passed_count=0,
            )

        if not tool_result.success:
            fb_type = FeedbackParser._classify_failure(combined)
            suggestion = FeedbackParser._get_suggestion(fb_type, combined)
            failed, passed = FeedbackParser._parse_pytest_counts(combined)

            # Extract the most relevant detail
            detail = FeedbackParser._extract_error_detail(combined)

            return Feedback(
                type=fb_type,
                summary=f"{'Test' if failed > 0 else 'Command'} failed with {fb_type.value}",
                detail=detail,
                suggestion=suggestion,
                failed_count=failed,
                passed_count=passed,
            )

        # Success case
        failed, passed = FeedbackParser._parse_pytest_counts(combined)
        return Feedback(
            type=FeedbackType.UNKNOWN,
            summary="Command executed successfully",
            detail=combined[:500],
            suggestion="",
            failed_count=failed,
            passed_count=passed,
        )

    @staticmethod
    def _classify_failure(combined: str) -> FeedbackType:
        """Classify the type of failure from the output."""
        if re.search(r"SyntaxError", combined):
            return FeedbackType.SYNTAX_ERROR
        if re.search(r"AssertionError|assert\b", combined):
            return FeedbackType.ASSERTION_FAILURE
        if re.search(r"ImportError|ModuleNotFoundError", combined):
            return FeedbackType.IMPORT_ERROR
        if re.search(r"timeout|timed out", combined, re.IGNORECASE):
            return FeedbackType.TIMEOUT
        return FeedbackType.UNKNOWN

    @staticmethod
    def _get_suggestion(fb_type: FeedbackType, combined: str) -> str:
        """Generate a suggestion based on failure type."""
        suggestions = {
            FeedbackType.SYNTAX_ERROR: "Fix the syntax error in the code.",
            FeedbackType.ASSERTION_FAILURE: "Check the logic — the expected value does not match the actual value.",
            FeedbackType.IMPORT_ERROR: "Install the missing dependency or check the import path.",
            FeedbackType.TIMEOUT: "The command took too long. Consider optimizing or splitting the work.",
            FeedbackType.UNKNOWN: "Review the error output and determine the root cause.",
        }
        return suggestions.get(fb_type, "")

    @staticmethod
    def _parse_pytest_counts(combined: str) -> tuple[int, int]:
        """Extract passed/failed counts from pytest output."""
        match = re.search(r"(\d+)\s+failed,\s*(\d+)\s+passed", combined)
        if match:
            return int(match.group(1)), int(match.group(2))
        match = re.search(r"(\d+)\s+passed", combined)
        if match:
            return 0, int(match.group(1))
        return 0, 0

    @staticmethod
    def _extract_error_detail(combined: str) -> str:
        """Extract the most relevant error lines from the output."""
        lines = combined.split("\n")
        error_lines = []
        for line in lines:
            line_stripped = line.strip()
            if not line_stripped:
                continue
            if any(kw in line_stripped for kw in [
                "FAILED", "ERROR", "Error", "assert", "SyntaxError",
                "ImportError", "ModuleNotFoundError", "Traceback",
            ]):
                error_lines.append(line_stripped)
        if not error_lines:
            error_lines = lines[-5:]  # last 5 lines as fallback
        return "\n".join(error_lines[:10])  # max 10 lines

    @staticmethod
    def to_message(feedback: Feedback) -> str:
        """Convert a Feedback object to a message string for the LLM context."""
        parts = [
            f"[FEEDBACK] {feedback.summary}",
            f"Type: {feedback.type.value}",
            f"FAILED: {feedback.failed_count} failed, {feedback.passed_count} passed",
        ]
        if feedback.detail:
            parts.append(f"Details:\n{feedback.detail}")
        if feedback.suggestion:
            parts.append(f"Suggestion: {feedback.suggestion}")
        return "\n".join(parts)