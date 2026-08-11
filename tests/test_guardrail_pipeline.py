"""Tests for guardrail pipeline."""
import pytest
from src.models import Action, GuardrailResult
from src.guardrails.base import Guardrail, GuardrailPipeline
from src.guardrails.factory import create_guardrail_pipeline


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


def test_create_pipeline_from_config(sample_config_dict):
    pipeline = create_guardrail_pipeline(sample_config_dict)
    assert pipeline is not None
    # Should have 4 layers: FileFence, CommandClassifier, HITLGuard, SandboxExecutor
    assert len(pipeline._layers) == 4


@pytest.mark.asyncio
async def test_full_pipeline_with_safe_command(sample_config_dict):
    pipeline = create_guardrail_pipeline(sample_config_dict)
    action = Action(tool_name="run_shell", arguments={"cmd": "pytest tests/"})
    result = await pipeline.check(action)
    assert result.blocked is False


@pytest.mark.asyncio
async def test_full_pipeline_with_dangerous_command(sample_config_dict):
    pipeline = create_guardrail_pipeline(sample_config_dict)
    action = Action(tool_name="run_shell", arguments={"cmd": "rm -rf /"})
    result = await pipeline.check(action)
    # rm -rf / is classified as dangerous, but HITL is not called
    # because the pipeline only checks, doesn't execute HITL in check()
    # The HITL is triggered separately when level is dangerous
    assert result.level == "dangerous"


@pytest.mark.asyncio
async def test_full_pipeline_file_fence_first(sample_config_dict):
    """File fence should block paths before command classification."""
    pipeline = create_guardrail_pipeline(sample_config_dict)
    action = Action(tool_name="read_file", arguments={"path": "/etc/passwd"})
    result = await pipeline.check(action)
    assert result.blocked is True
    assert "outside" in result.reason.lower()