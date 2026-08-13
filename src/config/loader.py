"""Configuration loader with YAML parsing and validation."""
from pathlib import Path
import yaml


REQUIRED_TOP_KEYS = ["loop", "llm", "tools", "guardrails", "memory"]


class ConfigLoader:
    """Load and validate harness configuration from YAML files."""

    def load(self, path: str) -> dict:
        """Load a YAML config file and validate its structure.

        Args:
            path: Path to the YAML config file.

        Returns:
            Validated config dict.

        Raises:
            FileNotFoundError: If the config file does not exist.
            ValueError: If the YAML is invalid or missing required keys.
        """
        config_path = Path(path).expanduser()
        if not config_path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")

        try:
            content = config_path.read_text(encoding="utf-8")
            config = yaml.safe_load(content)
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML in {config_path}: {e}") from e

        if config is None:
            raise ValueError(f"Config file is empty: {config_path}")

        self._validate(config, config_path)
        return config

    def _validate(self, config: dict, path: Path) -> None:
        """Validate that all required top-level keys are present."""
        for key in REQUIRED_TOP_KEYS:
            if key not in config:
                raise ValueError(
                    f"Missing required key '{key}' in config: {path}"
                )