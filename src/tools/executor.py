"""Tool executor — dispatches tool calls to actual implementations."""
import asyncio
import os
from pathlib import Path
from src.models import ToolCall, ToolResult


async def execute_tool(tool_call: ToolCall, cwd: str = ".", timeout: int = 60) -> ToolResult:
    """Execute a single tool call and return the result.

    Args:
        tool_call: The tool call to execute.
        cwd: Working directory for shell commands.
        timeout: Timeout in seconds for shell commands.

    Returns:
        ToolResult with stdout, stderr, exit_code, and success flag.
    """
    name = tool_call.name
    args = tool_call.arguments

    if name == "read_file":
        return await _read_file(args.get("path", ""))
    elif name == "write_file":
        return await _write_file(args.get("path", ""), args.get("content", ""))
    elif name == "run_shell":
        return await _run_shell(args.get("cmd", ""), args.get("cwd", cwd), timeout)
    elif name == "finish":
        return await _finish(args.get("summary", ""))
    else:
        return ToolResult(
            tool_call_id=tool_call.id,
            tool_name=name,
            success=False,
            stdout="",
            stderr=f"Unknown tool: {name}",
            exit_code=-1,
        )


async def _read_file(path: str) -> ToolResult:
    try:
        content = Path(path).read_text(encoding="utf-8")
        return ToolResult(
            tool_call_id="",
            tool_name="read_file",
            success=True,
            stdout=content,
            stderr="",
            exit_code=0,
        )
    except FileNotFoundError:
        return ToolResult(
            tool_call_id="",
            tool_name="read_file",
            success=False,
            stdout="",
            stderr=f"File not found: {path}",
            exit_code=1,
        )
    except Exception as e:
        return ToolResult(
            tool_call_id="",
            tool_name="read_file",
            success=False,
            stdout="",
            stderr=str(e),
            exit_code=1,
        )


async def _write_file(path: str, content: str) -> ToolResult:
    try:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return ToolResult(
            tool_call_id="",
            tool_name="write_file",
            success=True,
            stdout=f"Written {len(content)} bytes to {path}",
            stderr="",
            exit_code=0,
        )
    except Exception as e:
        return ToolResult(
            tool_call_id="",
            tool_name="write_file",
            success=False,
            stdout="",
            stderr=str(e),
            exit_code=1,
        )


async def _run_shell(cmd: str, cwd: str, timeout: int) -> ToolResult:
    try:
        proc = await asyncio.create_subprocess_shell(
            cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=cwd,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        exit_code = proc.returncode or 0
        return ToolResult(
            tool_call_id="",
            tool_name="run_shell",
            success=exit_code == 0,
            stdout=stdout.decode("utf-8", errors="replace"),
            stderr=stderr.decode("utf-8", errors="replace"),
            exit_code=exit_code,
        )
    except asyncio.TimeoutError:
        return ToolResult(
            tool_call_id="",
            tool_name="run_shell",
            success=False,
            stdout="",
            stderr=f"Command timeout after {timeout}s: {cmd}",
            exit_code=-1,
        )
    except Exception as e:
        return ToolResult(
            tool_call_id="",
            tool_name="run_shell",
            success=False,
            stdout="",
            stderr=str(e),
            exit_code=1,
        )


async def _finish(summary: str) -> ToolResult:
    return ToolResult(
        tool_call_id="",
        tool_name="finish",
        success=True,
        stdout=f"Task finished: {summary}",
        stderr="",
        exit_code=0,
    )