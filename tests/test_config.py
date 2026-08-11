"""Tests for configuration loader."""
import pytest
import tempfile
from pathlib import Path
from src.config.loader import ConfigLoader


@pytest.fixture
def config_file(sample_config_dict):
    """Write a temporary YAML config file for testing."""
    import yaml
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".yaml", delete=False
    ) as f:
        yaml.dump(sample_config_dict, f)
        return Path(f.name)


def test_load_valid_config(config_file, sample_config_dict):
    loader = ConfigLoader()
    config = loader.load(str(config_file))
    assert config["loop"]["max_turns"] == 20
    assert config["llm"]["model"] == "gpt-4o"


def test_load_missing_file():
    loader = ConfigLoader()
    with pytest.raises(FileNotFoundError):
        loader.load("/nonexistent/config.yaml")


def test_load_invalid_yaml(temp_dir):
    bad_file = temp_dir / "bad.yaml"
    bad_file.write_text("invalid: [:: yaml")
    loader = ConfigLoader()
    with pytest.raises(ValueError, match="Invalid YAML"):
        loader.load(str(bad_file))


def test_validate_missing_required_keys(temp_dir, sample_config_dict):
    import yaml
    del sample_config_dict["loop"]
    bad_file = temp_dir / "partial.yaml"
    bad_file.write_text(yaml.dump(sample_config_dict))
    loader = ConfigLoader()
    with pytest.raises(ValueError, match="Missing required key"):
        loader.load(str(bad_file))


def test_get_guardrail_config(config_file):
    loader = ConfigLoader()
    config = loader.load(str(config_file))
    guardrail = config["guardrails"]
    assert "allowed_paths" in guardrail
    assert "command_rules" in guardrail
    assert guardrail["hitl"]["timeout"] == 30


def test_default_config_exists():
    """Verify the default harness.yaml is loadable."""
    from pathlib import Path
    default_path = Path(__file__).parent.parent / "src" / "harness.yaml"
    if default_path.exists():
        loader = ConfigLoader()
        config = loader.load(str(default_path))
        assert "loop" in config
        assert "guardrails" in config