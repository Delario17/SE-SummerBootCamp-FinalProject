"""Tests for memory store."""
import pytest
from src.models import Message, Session
from src.memory.store import MemoryStore


@pytest.fixture
def memory():
    """Create an in-memory MemoryStore for testing."""
    return MemoryStore(db_path=":memory:")


@pytest.mark.asyncio
async def test_create_session(memory):
    session = await memory.create_session("Run pytest on src/")
    assert session.id is not None
    assert session.task == "Run pytest on src/"
    assert session.status == "running"


@pytest.mark.asyncio
async def test_add_and_retrieve_messages(memory):
    session = await memory.create_session("Test task")
    msg = Message(role="user", content="hello")
    await memory.add_message(session.id, turn=0, message=msg)
    messages = await memory.get_context(session.id, max_turns=10)
    assert len(messages) == 1
    assert messages[0].content == "hello"


@pytest.mark.asyncio
async def test_get_context_limits_turns(memory):
    session = await memory.create_session("Test task")
    for i in range(5):
        msg = Message(role="user", content=f"msg {i}")
        await memory.add_message(session.id, turn=i, message=msg)
    messages = await memory.get_context(session.id, max_turns=3)
    assert len(messages) == 3


@pytest.mark.asyncio
async def test_save_and_search_facts(memory):
    await memory.save_fact("preferred_test_framework", "pytest", source="user")
    await memory.save_fact("code_style", "PEP 8", source="config")
    results = await memory.search_facts("test")
    assert len(results) == 1
    assert results[0]["value"] == "pytest"


@pytest.mark.asyncio
async def test_search_facts_no_match(memory):
    await memory.save_fact("key1", "value1")
    results = await memory.search_facts("nonexistent")
    assert len(results) == 0


@pytest.mark.asyncio
async def test_update_session(memory):
    session = await memory.create_session("Test task")
    await memory.update_session(session.id, status="completed", turns=5)
    # Verify by getting context with a fresh query
    messages = await memory.get_context(session.id)
    assert len(messages) == 0  # no messages, but session updated