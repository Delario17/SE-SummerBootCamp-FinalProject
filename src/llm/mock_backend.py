"""Mock LLM backend for deterministic testing."""
from src.models import Message, LLMResponse
from src.llm.base import LLMBackend


class MockLLMBackend:
    """Returns pre-configured responses in sequence. No real LLM calls."""

    def __init__(self, responses: list[LLMResponse]):
        if not responses:
            raise ValueError("responses must not be empty")
        self._responses = responses
        self._index = 0
        self.call_count = 0

    async def chat(
        self, messages: list[Message], tools: list[dict]
    ) -> LLMResponse:
        if self._index >= len(self._responses):
            raise RuntimeError(
                f"No more mock responses (used {self._index}/{len(self._responses)})"
            )
        response = self._responses[self._index]
        self._index += 1
        self.call_count += 1
        return response