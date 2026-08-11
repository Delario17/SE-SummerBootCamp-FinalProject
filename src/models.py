"""Core data models for the Coding Agent Harness."""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Literal, Optional


class CommandLevel(str, Enum):
    SAFE = "safe"
    WARN = "warn"
    DANGEROUS = "dangerous"


class FeedbackType(str, Enum):
    SYNTAX_ERROR = "SYNTAX_ERROR"
    ASSERTION_FAILURE = "ASSERTION_FAILURE"
    IMPORT_ERROR = "IMPORT_ERROR"
    TIMEOUT = "TIMEOUT"
    UNKNOWN = "UNKNOWN"


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict[str, Any]


@dataclass
class Message:
    role: Literal["system", "user", "assistant", "tool"]
    content: Optional[str] = None
    tool_calls: Optional[list[ToolCall]] = None
    tool_call_id: Optional[str] = None
    name: Optional[str] = None


@dataclass
class ToolResult:
    tool_call_id: str
    tool_name: str
    success: bool
    stdout: str
    stderr: str
    exit_code: int
    duration_ms: float = 0.0


@dataclass
class GuardrailResult:
    allowed: bool
    level: str
    reason: Optional[str] = None
    requires_hitl: bool = False
    blocked: bool = False


@dataclass
class Feedback:
    type: FeedbackType
    summary: str
    detail: str
    suggestion: str = ""
    failed_count: int = 0
    passed_count: int = 0


@dataclass
class LLMResponse:
    content: Optional[str] = None
    tool_calls: Optional[list[ToolCall]] = None
    finish_reason: str = "stop"
    usage: Optional[dict[str, int]] = None


@dataclass
class Action:
    tool_name: str
    arguments: dict[str, Any]


@dataclass
class Session:
    id: str
    task: str
    status: str = "running"
    turns: int = 0
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None