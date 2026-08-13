"""Tests for CLI interface."""
import pytest
from click.testing import CliRunner
from src.cli.main import cli


@pytest.fixture
def runner():
    return CliRunner()


def test_cli_help(runner):
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "run" in result.output
    assert "setup" in result.output


def test_cli_run_help(runner):
    result = runner.invoke(cli, ["run", "--help"])
    assert result.exit_code == 0


def test_cli_setup_help(runner):
    result = runner.invoke(cli, ["setup", "--help"])
    assert result.exit_code == 0


def test_cli_run_no_args(runner):
    """run command without task should show error."""
    result = runner.invoke(cli, ["run"])
    assert result.exit_code != 0