"""HITL (Human-in-the-Loop) guardrail — requires human approval for dangerous actions."""
import asyncio
from collections.abc import Callable
from src.models import Action, GuardrailResult


class HITLGuard:
    """Pauses execution for dangerous actions, waiting for human approval."""

    def __init__(
        self,
        timeout: float = 30.0,
        input_func: Callable[[str], str | None] | None = None,
    ):
        self._timeout = timeout
        self._input_func = input_func or input

    async def check(self, action: Action) -> GuardrailResult:
        """Check if the action requires HITL approval. Does not prompt.

        The pipeline only evaluates -- actual prompting is done by the agent
        loop when requires_hitl is True.
        """
        if action.tool_name != "run_shell":
            return GuardrailResult(
                allowed=True, level="safe",
                reason=None, requires_hitl=False, blocked=False,
            )
        return GuardrailResult(
            allowed=True, level="dangerous",
            reason="requires human approval",
            requires_hitl=True, blocked=False,
        )

    async def request_approval(self, action: Action) -> GuardrailResult:
        """Request human approval for a dangerous action."""
        cmd = action.arguments.get("cmd", "unknown")
        prompt = (
            f"\n[HITL] Dangerous command detected:\n"
            f"  Command: {cmd}\n"
            f"  Risk: This command could cause data loss or system damage.\n"
            f"  Approve? (y/n, timeout={self._timeout}s): "
        )

        try:
            response = await self._get_input(prompt)
            if response is None:
                return GuardrailResult(
                    allowed=False, level="dangerous",
                    reason="timeout", requires_hitl=True, blocked=True,
                )
            if response.strip().lower() in ("y", "yes"):
                return GuardrailResult(
                    allowed=True, level="dangerous",
                    reason="approved by human", requires_hitl=True, blocked=False,
                )
            else:
                return GuardrailResult(
                    allowed=False, level="dangerous",
                    reason="rejected by human", requires_hitl=True, blocked=True,
                )
        except asyncio.TimeoutError:
            return GuardrailResult(
                allowed=False, level="dangerous",
                reason="timeout", requires_hitl=True, blocked=True,
            )

    async def _get_input(self, prompt: str) -> str | None:
        """Get user input with a timeout."""
        try:
            loop = asyncio.get_running_loop()
            result = await asyncio.wait_for(
                loop.run_in_executor(None, self._input_func, prompt),
                timeout=self._timeout,
            )
            return result
        except asyncio.TimeoutError:
            return None