"""Tests for command classifier guardrail."""
import pytest
from src.models import Action, CommandLevel
from src.guardrails.command_classifier import CommandClassifier


@pytest.fixture
def classifier():
    rules = [
        {
            "pattern": r"^(ls|cat|pytest|flake8|mypy|python|pip(?! install)|git status|git diff|echo|mkdir|touch)\b",
            "level": "safe",
        },
        {
            "pattern": r"^(git commit|git checkout|git branch|pip install|npm install)\b",
            "level": "warn",
        },
        {
            "pattern": r"\brm -rf\b|\bDROP TABLE\b|\bDELETE FROM\b|git push --force|chmod 777|\bsudo\b|> /dev/|\bmkfs\b|\bdd if=",
            "level": "dangerous",
        },
    ]
    return CommandClassifier(rules=rules)


@pytest.mark.asyncio
async def test_classify_safe_commands(classifier):
    safe_cmds = ["ls", "pytest tests/", "cat file.py", "echo hello", "mkdir tmp"]
    for cmd in safe_cmds:
        action = Action(tool_name="run_shell", arguments={"cmd": cmd})
        result = await classifier.check(action)
        assert result.blocked is False, f"Command '{cmd}' should be safe"
        assert result.level == "safe"


@pytest.mark.asyncio
async def test_classify_warn_commands(classifier):
    warn_cmds = ["git commit -m 'msg'", "git checkout main", "pip install flask"]
    for cmd in warn_cmds:
        action = Action(tool_name="run_shell", arguments={"cmd": cmd})
        result = await classifier.check(action)
        assert result.blocked is False, f"Command '{cmd}' should be warn"
        assert result.level == "warn"


@pytest.mark.asyncio
async def test_classify_dangerous_commands(classifier):
    dangerous_cmds = [
        "rm -rf /",
        "rm -rf ./src",
        "DROP TABLE users",
        "DELETE FROM users WHERE 1=1",
        "git push --force origin main",
        "chmod 777 /tmp",
        "sudo rm -rf /",
        "mkfs /dev/sda",
    ]
    for cmd in dangerous_cmds:
        action = Action(tool_name="run_shell", arguments={"cmd": cmd})
        result = await classifier.check(action)
        assert result.blocked is False, f"Command '{cmd}' should be dangerous (not blocked, just classified)"
        assert result.level == "dangerous"


@pytest.mark.asyncio
async def test_skips_non_shell_actions(classifier):
    action = Action(tool_name="read_file", arguments={"path": "test.py"})
    result = await classifier.check(action)
    assert result.blocked is False
    assert result.level == "safe"


@pytest.mark.asyncio
async def test_unknown_command_defaults_to_safe(classifier):
    """Commands not matching any rule default to safe."""
    action = Action(tool_name="run_shell", arguments={"cmd": "custom-tool --flag"})
    result = await classifier.check(action)
    assert result.level == "safe"
    assert result.blocked is False


@pytest.mark.asyncio
async def test_first_match_wins():
    """The first matching rule determines the level."""
    rules = [
        {"pattern": r"^rm\b", "level": "safe"},       # matches first
        {"pattern": r"rm -rf", "level": "dangerous"},  # would match too
    ]
    classifier = CommandClassifier(rules=rules)
    action = Action(tool_name="run_shell", arguments={"cmd": "rm -rf /"})
    result = await classifier.check(action)
    assert result.level == "safe"  # first rule wins