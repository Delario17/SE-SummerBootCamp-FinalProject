"""Tests for guardrail pipeline."""
import pytest
from src.models import Action, GuardrailResult
from src.guardrails.base import Guardrail, GuardrailPipeline


class FakeBlockGuardrail:
    """A guardrail that always blocks."""
    async def check(self, action: Action) -> GuardrailResult:
        return GuardrailResult(
            allowed=False, level="dangerous",
            reason="always blocked", requires_hitl=False, blocked=True,
        )


class FakePassGuardrail:
    """A guardrail that always passes."""
    async def check(self, action: Action) -> GuardrailResult:
        return GuardrailResult(
            allowed=True, level="safe",
            reason=None, requires_hitl=False, blocked=False,
        )


@pytest.mark.asyncio
async def test_pipeline_stops_at_first_block():
    pipeline = GuardrailPipeline([
        FakeBlockGuardrail(),
        FakePassGuardrail(),
    ])
    action = Action(tool_name="run_shell", arguments={"cmd": "ls"})
    result = await pipeline.check(action)
    assert result.blocked is True
    assert result.reason == "always blocked"


@pytest.mark.asyncio
async def test_pipeline_passes_when_all_pass():
    pipeline = GuardrailPipeline([
        FakePassGuardrail(),
        FakePassGuardrail(),
    ])
    action = Action(tool_name="run_shell", arguments={"cmd": "ls"})
    result = await pipeline.check(action)
    assert result.blocked is False
    assert result.allowed is True


@pytest.mark.asyncio
async def test_pipeline_empty_passes():
    pipeline = GuardrailPipeline([])
    action = Action(tool_name="run_shell", arguments={"cmd": "ls"})
    result = await pipeline.check(action)
    assert result.blocked is False


@pytest.mark.asyncio
async def test_fake_guardrail_satisfies_protocol():
    g = FakePassGuardrail()
    assert isinstance(g, Guardrail)