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