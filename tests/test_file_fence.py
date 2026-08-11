"""Tests for file system fence guardrail."""
import pytest
from pathlib import Path
from src.models import Action
from src.guardrails.file_fence import FileFence


@pytest.fixture
def fence():
    return FileFence(allowed_paths=["./src", "./tests", "./demo"])


@pytest.mark.asyncio
async def test_blocks_read_outside_fence(fence):
    action = Action(tool_name="read_file", arguments={"path": "/etc/passwd"})
    result = await fence.check(action)
    assert result.blocked is True
    assert "outside allowed paths" in result.reason.lower()


@pytest.mark.asyncio
async def test_blocks_write_outside_fence(fence):
    action = Action(tool_name="write_file", arguments={"path": "/usr/bin/malware"})
    result = await fence.check(action)
    assert result.blocked is True


@pytest.mark.asyncio
async def test_allows_read_inside_fence(fence, temp_dir):
    # Create a file inside a fake ./src structure
    src_dir = temp_dir / "src"
    src_dir.mkdir()
    test_file = src_dir / "main.py"
    test_file.write_text("code")
    fence2 = FileFence(allowed_paths=[str(src_dir)])
    action = Action(tool_name="read_file", arguments={"path": str(test_file)})
    result = await fence2.check(action)
    assert result.blocked is False


@pytest.mark.asyncio
async def test_allows_write_inside_fence(fence, temp_dir):
    src_dir = temp_dir / "src"
    src_dir.mkdir()
    fence2 = FileFence(allowed_paths=[str(src_dir)])
    action = Action(tool_name="write_file", arguments={
        "path": str(src_dir / "new.py"), "content": "x",
    })
    result = await fence2.check(action)
    assert result.blocked is False


@pytest.mark.asyncio
async def test_skips_non_file_actions(fence):
    """File fence should only check read_file and write_file actions."""
    action = Action(tool_name="run_shell", arguments={"cmd": "ls"})
    result = await fence.check(action)
    assert result.blocked is False


@pytest.mark.asyncio
async def test_resolves_relative_paths(fence, temp_dir):
    src_dir = temp_dir / "src"
    src_dir.mkdir()
    test_file = src_dir / "main.py"
    test_file.write_text("code")
    fence2 = FileFence(allowed_paths=[str(src_dir)])
    # Use relative path
    import os
    original_cwd = os.getcwd()
    try:
        os.chdir(temp_dir)
        action = Action(tool_name="read_file", arguments={"path": "src/main.py"})
        result = await fence2.check(action)
        assert result.blocked is False
    finally:
        os.chdir(original_cwd)