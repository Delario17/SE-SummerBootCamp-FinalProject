"""LLM Backend Protocol."""
from typing import Protocol, runtime_checkable
from src.models import Message, LLMResponse


@runtime_checkable
class LLMBackend(Protocol):
    """Protocol for LLM backends. Both real and mock implementations must satisfy this."""

    async def chat(
        self, messages: list[Message], tools: list[dict]
    ) -> LLMResponse:
        """Send messages to LLM and get a response (text or tool_calls)."""
        ...