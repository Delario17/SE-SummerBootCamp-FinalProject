"""Tests for tool schemas and executor."""
import pytest
from src.tools.schema import TOOL_SCHEMAS, get_tool_schema, get_allowed_tools


def test_all_four_tools_defined():
    names = [t["function"]["name"] for t in TOOL_SCHEMAS]
    assert "read_file" in names
    assert "write_file" in names
    assert "run_shell" in names
    assert "finish" in names


def test_read_file_schema():
    schema = get_tool_schema("read_file")
    assert schema["function"]["name"] == "read_file"
    assert "path" in schema["function"]["parameters"]["properties"]
    assert "path" in schema["function"]["parameters"]["required"]


def test_write_file_schema():
    schema = get_tool_schema("write_file")
    props = schema["function"]["parameters"]["properties"]
    assert "path" in props
    assert "content" in props
    assert set(schema["function"]["parameters"]["required"]) == {"path", "content"}


def test_run_shell_schema():
    schema = get_tool_schema("run_shell")
    props = schema["function"]["parameters"]["properties"]
    assert "cmd" in props
    assert "cwd" in props


def test_finish_schema():
    schema = get_tool_schema("finish")
    props = schema["function"]["parameters"]["properties"]
    assert "summary" in props


def test_get_tool_schema_unknown():
    with pytest.raises(ValueError, match="Unknown tool"):
        get_tool_schema("nonexistent_tool")


def test_get_allowed_tools_filters():
    allowed = get_allowed_tools(["read_file", "finish"])
    names = [t["function"]["name"] for t in allowed]
    assert names == ["read_file", "finish"]


def test_get_allowed_tools_all():
    allowed = get_allowed_tools(["read_file", "write_file", "run_shell", "finish"])
    assert len(allowed) == 4


# --- Executor Tests ---

import time
from src.models import ToolCall, ToolResult
from src.tools.executor import execute_tool


@pytest.mark.asyncio
async def test_execute_read_file(temp_dir):
    test_file = temp_dir / "test.txt"
    test_file.write_text("hello world")
    tc = ToolCall(id="c1", name="read_file", arguments={"path": str(test_file)})
    result = await execute_tool(tc)
    assert result.success is True
    assert result.stdout == "hello world"
    assert result.exit_code == 0


@pytest.mark.asyncio
async def test_execute_read_file_not_found():
    tc = ToolCall(id="c1", name="read_file", arguments={"path": "/nonexistent/file.txt"})
    result = await execute_tool(tc)
    assert result.success is False
    assert "not found" in result.stderr.lower()


@pytest.mark.asyncio
async def test_execute_write_file(temp_dir):
    test_file = temp_dir / "output.txt"
    tc = ToolCall(id="c1", name="write_file", arguments={
        "path": str(test_file), "content": "new content",
    })
    result = await execute_tool(tc)
    assert result.success is True
    assert test_file.read_text() == "new content"


@pytest.mark.asyncio
async def test_execute_write_file_creates_dirs(temp_dir):
    test_file = temp_dir / "subdir" / "nested" / "file.txt"
    tc = ToolCall(id="c1", name="write_file", arguments={
        "path": str(test_file), "content": "nested",
    })
    result = await execute_tool(tc)
    assert result.success is True
    assert test_file.read_text() == "nested"


@pytest.mark.asyncio
async def test_execute_run_shell_success():
    tc = ToolCall(id="c1", name="run_shell", arguments={"cmd": "echo hello"})
    result = await execute_tool(tc)
    assert result.success is True
    assert "hello" in result.stdout
    assert result.exit_code == 0


@pytest.mark.asyncio
async def test_execute_run_shell_failure():
    tc = ToolCall(id="c1", name="run_shell", arguments={"cmd": "python -c 'exit(1)'"})
    result = await execute_tool(tc)
    assert result.success is False
    assert result.exit_code == 1


@pytest.mark.asyncio
async def test_execute_run_shell_timeout():
    tc = ToolCall(id="c1", name="run_shell", arguments={"cmd": "sleep 10"})
    result = await execute_tool(tc, timeout=1)
    assert result.success is False
    assert "timeout" in result.stderr.lower()


@pytest.mark.asyncio
async def test_execute_finish():
    tc = ToolCall(id="c1", name="finish", arguments={"summary": "All done"})
    result = await execute_tool(tc)
    assert result.success is True
    assert "All done" in result.stdout


@pytest.mark.asyncio
async def test_execute_unknown_tool():
    tc = ToolCall(id="c1", name="unknown_tool", arguments={})
    result = await execute_tool(tc)
    assert result.success is False
    assert "Unknown tool" in result.stderr