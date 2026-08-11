"""Guardrail protocol and pipeline base classes."""
from typing import Protocol, runtime_checkable
from src.models import Action, GuardrailResult


@runtime_checkable
class Guardrail(Protocol):
    """Protocol for individual guardrail checks.

    Each guardrail layer implements this protocol.
    """

    async def check(self, action: Action) -> GuardrailResult:
        """Check an action and return a guardrail result.

        Args:
            action: The action (tool call) to check.

        Returns:
            GuardrailResult indicating whether the action is allowed.
        """
        ...


class GuardrailPipeline:
    """Pipeline that runs multiple guardrail layers in sequence.

    Stops at the first layer that blocks the action.
    """

    def __init__(self, layers: list[Guardrail]):
        self._layers = layers

    async def check(self, action: Action) -> GuardrailResult:
        """Run all guardrail layers in order. Returns first blocking result."""
        last_result = None
        for layer in self._layers:
            result = await layer.check(action)
            if result.blocked:
                return result
            # Preserve the last meaningful result (skip neutral pass-through)
            if result.level != "safe" or result.reason is not None:
                last_result = result
        return last_result or GuardrailResult(
            allowed=True, level="safe",
            reason=None, requires_hitl=False, blocked=False,
        )