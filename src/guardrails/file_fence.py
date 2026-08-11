"""File system fence guardrail — restricts file access to allowed paths."""
from pathlib import Path
from src.models import Action, GuardrailResult


class FileFence:
    """Restricts file read/write operations to a whitelist of allowed directories."""

    def __init__(self, allowed_paths: list[str]):
        self._allowed = [Path(p).resolve() for p in allowed_paths]

    async def check(self, action: Action) -> GuardrailResult:
        """Check if the action's file path is within allowed directories."""
        if action.tool_name not in ("read_file", "write_file"):
            return GuardrailResult(
                allowed=True, level="safe",
                reason=None, requires_hitl=False, blocked=False,
            )

        path_str = action.arguments.get("path", "")
        if not path_str:
            return GuardrailResult(
                allowed=False, level="dangerous",
                reason="No path provided for file operation", blocked=True,
            )

        target = Path(path_str).resolve()

        for allowed in self._allowed:
            try:
                target.relative_to(allowed)
                return GuardrailResult(
                    allowed=True, level="safe",
                    reason=None, requires_hitl=False, blocked=False,
                )
            except ValueError:
                continue

        return GuardrailResult(
            allowed=False, level="dangerous",
            reason=f"File path '{path_str}' is outside allowed paths: {self._allowed}",
            blocked=True,
        )