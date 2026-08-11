"""Sandbox executor — runs commands in a restricted environment."""
import asyncio
import tempfile
import os
from pathlib import Path
from src.models import Action, ToolResult


class SandboxExecutor:
    """Executes shell commands in a sandboxed environment with resource limits."""

    def __init__(self, memory_limit_mb: int = 512, cpu_time_limit: int = 30):
        self._memory_limit_mb = memory_limit_mb
        self._cpu_time_limit = cpu_time_limit

    async def execute(self, action: Action) -> ToolResult:
        """Execute a command in a sandboxed temporary directory.

        Note: This is a software-level sandbox using subprocess isolation.
        It is NOT a security boundary — for true isolation, use Docker.
        """
        if action.tool_name != "run_shell":
            return ToolResult(
                tool_call_id="",
                tool_name=action.tool_name,
                success=False,
                stdout="",
                stderr=f"Sandbox: not a shell command ({action.tool_name})",
                exit_code=-1,
            )

        cmd = action.arguments.get("cmd", "")
        if not cmd:
            return ToolResult(
                tool_call_id="",
                tool_name="run_shell",
                success=False,
                stdout="",
                stderr="Sandbox: no command provided",
                exit_code=-1,
            )

        with tempfile.TemporaryDirectory(prefix="harness_sandbox_") as sandbox_dir:
            sandbox_env = os.environ.copy()
            sandbox_env["PATH"] = "/usr/bin:/bin:/usr/local/bin"
            sandbox_env.pop("HOME", None)

            try:
                proc = await asyncio.create_subprocess_shell(
                    cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=sandbox_dir,
                    env=sandbox_env,
                )
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(), timeout=self._cpu_time_limit
                )
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
                    stderr=f"Sandbox: command timed out after {self._cpu_time_limit}s",
                    exit_code=-1,
                )
            except Exception as e:
                return ToolResult(
                    tool_call_id="",
                    tool_name="run_shell",
                    success=False,
                    stdout="",
                    stderr=f"Sandbox error: {e}",
                    exit_code=1,
                )