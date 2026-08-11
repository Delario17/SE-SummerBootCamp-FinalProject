"""Command classifier guardrail — categorizes shell commands by risk level."""
import re
from src.models import Action, GuardrailResult


class CommandClassifier:
    """Classifies shell commands into safe/warn/dangerous based on regex rules."""

    def __init__(self, rules: list[dict]):
        self._rules = [
            (re.compile(r["pattern"]), r["level"])
            for r in rules
        ]

    async def check(self, action: Action) -> GuardrailResult:
        """Classify the command in the action. Does not block — just labels."""
        if action.tool_name != "run_shell":
            return GuardrailResult(
                allowed=True, level="safe",
                reason=None, requires_hitl=False, blocked=False,
            )

        cmd = action.arguments.get("cmd", "")
        if not cmd:
            return GuardrailResult(
                allowed=True, level="safe",
                reason=None, requires_hitl=False, blocked=False,
            )

        for pattern, level in self._rules:
            if pattern.search(cmd):
                return GuardrailResult(
                    allowed=True, level=level,
                    reason=f"Command classified as {level}",
                    requires_hitl=(level == "dangerous"),
                    blocked=False,
                )

        return GuardrailResult(
            allowed=True, level="safe",
            reason=None, requires_hitl=False, blocked=False,
        )