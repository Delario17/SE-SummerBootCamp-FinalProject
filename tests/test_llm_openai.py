"""Tests for OpenAI-compatible backend."""
import pytest
from src.models import Message, ToolCall, LLMResponse
from src.llm.openai_backend import OpenAICompatBackend


def test_backend_initialization():
    backend = OpenAICompatBackend(
        api_key="test-key",
        model="gpt-4o",
        api_base="https://api.example.com/v1",
        temperature=0.1,
        max_tokens=4096,
    )
    assert backend.model == "gpt-4o"
    assert backend.api_base == "https://api.example.com/v1"


def test_convert_message_to_openai_format():
    backend = OpenAICompatBackend(
        api_key="test-key", model="gpt-4o", api_base="https://api.example.com/v1",
    )
    msg = Message(role="user", content="hello")
    result = backend._message_to_dict(msg)
    assert result == {"role": "user", "content": "hello"}


def test_convert_message_with_tool_calls():
    backend = OpenAICompatBackend(
        api_key="test-key", model="gpt-4o", api_base="https://api.example.com/v1",
    )
    tc = ToolCall(id="c1", name="read_file", arguments={"path": "test.py"})
    msg = Message(role="assistant", content=None, tool_calls=[tc])
    result = backend._message_to_dict(msg)
    assert result["role"] == "assistant"
    assert result["tool_calls"][0]["function"]["name"] == "read_file"


def test_convert_tool_message():
    backend = OpenAICompatBackend(
        api_key="test-key", model="gpt-4o", api_base="https://api.example.com/v1",
    )
    msg = Message(role="tool", content="file content", tool_call_id="c1", name="read_file")
    result = backend._message_to_dict(msg)
    assert result["role"] == "tool"
    assert result["tool_call_id"] == "c1"