"""Tests for Mock LLM Backend."""
import pytest
from src.models import Message, ToolCall, LLMResponse
from src.llm.mock_backend import MockLLMBackend


def make_text_response(content: str) -> LLMResponse:
    return LLMResponse(content=content, finish_reason="stop")


def make_tool_response(name: str, args: dict) -> LLMResponse:
    return LLMResponse(
        tool_calls=[ToolCall(id="call_1", name=name, arguments=args)],
        finish_reason="tool_calls",
    )


@pytest.mark.asyncio
async def test_mock_returns_sequence():
    responses = [
        make_text_response("Hello"),
        make_tool_response("read_file", {"path": "test.py"}),
        make_text_response("Done"),
    ]
    backend = MockLLMBackend(responses=responses)
    messages = [Message(role="user", content="hi")]

    r1 = await backend.chat(messages, tools=[])
    assert r1.content == "Hello"
    assert r1.finish_reason == "stop"

    r2 = await backend.chat(messages, tools=[])
    assert r2.tool_calls[0].name == "read_file"

    r3 = await backend.chat(messages, tools=[])
    assert r3.content == "Done"


@pytest.mark.asyncio
async def test_mock_raises_when_exhausted():
    backend = MockLLMBackend(responses=[make_text_response("only one")])
    messages = [Message(role="user", content="hi")]
    await backend.chat(messages, tools=[])
    with pytest.raises(RuntimeError, match="No more mock responses"):
        await backend.chat(messages, tools=[])


@pytest.mark.asyncio
async def test_mock_records_call_count():
    backend = MockLLMBackend(responses=[
        make_text_response("a"),
        make_text_response("b"),
    ])
    messages = [Message(role="user", content="hi")]
    await backend.chat(messages, tools=[])
    await backend.chat(messages, tools=[])
    assert backend.call_count == 2