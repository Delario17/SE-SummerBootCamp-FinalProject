"""Shared test fixtures."""
import pytest
import tempfile
import os
from pathlib import Path


@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing."""
    with tempfile.TemporaryDirectory() as d:
        yield Path(d)


@pytest.fixture
def sample_config_dict():
    """Return a minimal valid config dict for testing."""
    return {
        "loop": {"max_turns": 20, "idle_timeout": 3},
        "llm": {
            "provider": "openai_compat",
            "model": "gpt-4o",
            "api_base": "https://api.example.com/v1",
            "api_key_cmd": "echo test-key",
            "temperature": 0.1,
            "max_tokens": 4096,
        },
        "tools": {
            "allowed": ["read_file", "write_file", "run_shell", "finish"],
            "shell_timeout": 60,
        },
        "guardrails": {
            "allowed_paths": ["./src", "./tests"],
            "command_rules": [
                {"pattern": "^(ls|cat|pytest)\\b", "level": "safe"},
                {"pattern": "rm -rf", "level": "dangerous"},
            ],
            "hitl": {"timeout": 30, "enabled": True},
            "sandbox": {"enabled": False, "memory_limit_mb": 512, "cpu_time_limit": 30},
        },
        "memory": {"db_path": ":memory:", "max_context_turns": 10},
        "web": {"host": "0.0.0.0", "port": 8080},
    }