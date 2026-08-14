"""Agent main loop — orchestrates the full agent lifecycle."""
import logging
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
from src.models import (
    Message, Action, ToolCall, LLMResponse, ToolResult,
)
from src.llm.base import LLMBackend
from src.tools.executor import execute_tool
from src.tools.schema import get_allowed_tools
from src.feedback.parser import FeedbackParser
from src.guardrails.factory import create_guardrail_pipeline
from src.memory.store import MemoryStore
from src.config.loader import ConfigLoader

logger = logging.getLogger(__name__)


class StopReason(str, Enum):
    FINISH_CALLED = "finish_called"
    MAX_TURNS = "max_turns"
    IDLE_TIMEOUT = "idle_timeout"
    GUARDRAIL_BLOCKED = "guardrail_blocked"
    ERROR = "error"


@dataclass
class LoopResult:
    stop_reason: StopReason
    summary: str
    turns: int
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: datetime | None = None


class AgentLoop:
    """Main agent loop that orchestrates: context -> LLM -> parse -> guardrail -> dispatch -> feedback -> stop."""

    def __init__(self, config: dict):
        self._config = config
        self._loop_config = config.get("loop", {})
        self._max_turns = self._loop_config.get("max_turns", 20)
        self._idle_timeout = self._loop_config.get("idle_timeout", 3)
        self._tools_config = config.get("tools", {})
        self._allowed_tools = self._tools_config.get("allowed", [])
        self._shell_timeout = self._tools_config.get("shell_timeout", 60)
        self._guardrail_pipeline = create_guardrail_pipeline(config)
        from pathlib import Path
        db_path = config.get("memory", {}).get("db_path", ":memory:")
        if db_path != ":memory:":
            db_path = str(Path(db_path).expanduser())
        self._memory = MemoryStore(db_path=db_path)
        self._max_context_turns = config.get("memory", {}).get("max_context_turns", 10)

    async def run(self, task: str, llm_backend: LLMBackend) -> LoopResult:
        """Run the agent loop for a given task.

        Args:
            task: The user's task description.
            llm_backend: LLM backend to use (real or mock).

        Returns:
            LoopResult with stop reason, summary, and turn count.
        """
        result = LoopResult(stop_reason=StopReason.ERROR, summary="", turns=0)
        session = await self._memory.create_session(task)

        tools = get_allowed_tools(self._allowed_tools)
        messages = [
            Message(role="system", content=(
                "You are a coding agent. You can read files, write files, "
                "run shell commands, and declare tasks finished. "
                "Always use tools to interact with the system. "
                "When done, call the finish tool with a summary."
            )),
            Message(role="user", content=task),
        ]

        idle_count = 0
        consecutive_blocks = 0

        for turn in range(self._max_turns):
            result.turns = turn + 1

            # 1. Call LLM
            try:
                response = await llm_backend.chat(messages, tools)
            except Exception as e:
                logger.error(f"LLM call failed: {e}")
                result.stop_reason = StopReason.ERROR
                result.summary = f"LLM error: {e}"
                break

            # 2. Parse response
            if response.tool_calls:
                idle_count = 0
                for tc in response.tool_calls:
                    # Record assistant message
                    assistant_msg = Message(
                        role="assistant", content=None, tool_calls=[tc],
                    )
                    messages.append(assistant_msg)
                    await self._memory.add_message(session.id, turn, assistant_msg)

                    action = Action(tool_name=tc.name, arguments=tc.arguments)

                    # 3. Guardrail check
                    guard_result = await self._guardrail_pipeline.check(action)
                    if guard_result.blocked:
                        consecutive_blocks += 1
                        tool_result = ToolResult(
                            tool_call_id=tc.id,
                            tool_name=tc.name,
                            success=False,
                            stdout="",
                            stderr=f"BLOCKED by guardrail: {guard_result.reason}",
                            exit_code=-1,
                        )
                        await self._memory.log_audit(
                            session.id, "guardrail_block",
                            {"tool": tc.name, "args": tc.arguments, "reason": guard_result.reason},
                        )
                        if consecutive_blocks >= 3:
                            result.stop_reason = StopReason.GUARDRAIL_BLOCKED
                            result.summary = "Guardrail blocked 3 consecutive actions"
                            break
                    elif guard_result.requires_hitl:
                        # Check if HITL is enabled in config
                        hitl_enabled = self._config.get("guardrails", {}).get("hitl", {}).get("enabled", True)
                        if not hitl_enabled:
                            # HITL disabled — execute the tool directly
                            consecutive_blocks = 0
                            tool_result = await execute_tool(tc, timeout=self._shell_timeout)
                            await self._memory.log_audit(
                                session.id, "tool_execute",
                                {"tool": tc.name, "args": tc.arguments, "success": tool_result.success},
                            )
                        else:
                            # HITL approval
                            from src.guardrails.hitl import HITLGuard
                            hitl = HITLGuard(
                                timeout=self._config.get("guardrails", {}).get("hitl", {}).get("timeout", 30)
                            )
                            hitl_result = await hitl.request_approval(action)
                            if hitl_result.blocked:
                                tool_result = ToolResult(
                                    tool_call_id=tc.id,
                                    tool_name=tc.name,
                                    success=False,
                                    stdout="",
                                    stderr=f"HITL rejected: {hitl_result.reason}",
                                    exit_code=-1,
                                )
                                await self._memory.log_audit(
                                    session.id, "hitl_reject",
                                    {"tool": tc.name, "args": tc.arguments, "reason": hitl_result.reason},
                                )
                            else:
                                tool_result = await execute_tool(tc, timeout=self._shell_timeout)
                                await self._memory.log_audit(
                                    session.id, "hitl_approve",
                                    {"tool": tc.name, "args": tc.arguments},
                                )
                    else:
                        consecutive_blocks = 0
                        tool_result = await execute_tool(tc, timeout=self._shell_timeout)
                        await self._memory.log_audit(
                            session.id, "tool_execute",
                            {"tool": tc.name, "args": tc.arguments, "success": tool_result.success},
                        )

                    # 4. Record tool result
                    tool_msg = Message(
                        role="tool",
                        content=tool_result.stdout or tool_result.stderr,
                        tool_call_id=tc.id,
                        name=tc.name,
                    )
                    messages.append(tool_msg)

                    # 5. Feedback analysis
                    feedback = FeedbackParser.parse(tool_result)
                    if not tool_result.success:
                        feedback_msg = FeedbackParser.to_message(feedback)
                        messages.append(Message(role="user", content=feedback_msg))

                    # 6. Check if finish was called
                    if tc.name == "finish":
                        result.stop_reason = StopReason.FINISH_CALLED
                        result.summary = tc.arguments.get("summary", "Task completed")
                        break

                if result.stop_reason == StopReason.FINISH_CALLED:
                    break
                if result.stop_reason == StopReason.GUARDRAIL_BLOCKED:
                    break
            else:
                # Text response (no tool calls)
                idle_count += 1
                assistant_msg = Message(
                    role="assistant", content=response.content,
                )
                messages.append(assistant_msg)
                await self._memory.add_message(session.id, turn, assistant_msg)
                if idle_count >= self._idle_timeout:
                    result.stop_reason = StopReason.IDLE_TIMEOUT
                    result.summary = response.content or "Idle timeout reached"
                    break

        else:
            result.stop_reason = StopReason.MAX_TURNS
            result.summary = f"Reached max turns ({self._max_turns})"

        result.completed_at = datetime.now()
        await self._memory.update_session(session.id, result.stop_reason.value, result.turns)
        return result