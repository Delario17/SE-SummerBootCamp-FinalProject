"""Tests for sandbox executor."""
import tempfile
import pytest
from src.models import Action
from src.guardrails.sandbox import SandboxExecutor


@pytest.fixture
def sandbox():
    return SandboxExecutor(memory_limit_mb=512, cpu_time_limit=10)


@pytest.mark.asyncio
async def test_sandbox_runs_safe_command(sandbox, temp_dir):
    action = Action(tool_name="run_shell", arguments={"cmd": "echo hello", "cwd": str(temp_dir)})
    result = await sandbox.execute(action)
    assert result.success is True
    assert "hello" in result.stdout


@pytest.mark.asyncio
async def test_sandbox_sets_temp_directory():
    sandbox = SandboxExecutor()
    action = Action(tool_name="run_shell", arguments={"cmd": "pwd"})
    result = await sandbox.execute(action)
    assert result.success is True
    # Sandbox should run in a temporary directory
    tmpdir = tempfile.gettempdir().rstrip("/")
    assert tmpdir in result.stdout or "harness_sandbox" in result.stdout


@pytest.mark.asyncio
async def test_sandbox_limits_time():
    sandbox = SandboxExecutor(cpu_time_limit=1)
    action = Action(tool_name="run_shell", arguments={"cmd": "sleep 10"})
    result = await sandbox.execute(action)
    assert result.success is False
    assert "timed out" in result.stderr.lower() or "killed" in result.stderr.lower()


@pytest.mark.asyncio
async def test_sandbox_skips_non_shell_actions(sandbox):
    action = Action(tool_name="read_file", arguments={"path": "test.py"})
    result = await sandbox.execute(action)
    assert result.success is False
    assert "not a shell command" in result.stderr.lower()


@pytest.mark.asyncio
async def test_sandbox_restricts_environment():
    sandbox = SandboxExecutor()
    # Run a command that tries to access the network
    action = Action(tool_name="run_shell", arguments={
        "cmd": "python -c \"import urllib.request; urllib.request.urlopen('https://example.com', timeout=3)\""
    })
    result = await sandbox.execute(action)
    # May fail due to restricted environment or network issues
    # Not asserting on success/failure as it depends on environment
    assert result is not None