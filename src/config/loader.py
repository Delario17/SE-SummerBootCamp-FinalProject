"""Configuration loader with YAML parsing, validation, and multi-location search."""
from pathlib import Path
import yaml


REQUIRED_TOP_KEYS = ["loop", "llm", "tools", "guardrails", "memory"]

# Built-in default config — used as ultimate fallback
_DEFAULT_CONFIG = {
    "loop": {"max_turns": 20, "idle_timeout": 3},
    "llm": {
        "provider": "openai_compat",
        "model": "gpt-4o",
        "api_base": "https://your-relay.com/v1",
        "api_key_cmd": "keyring get harness",
        "temperature": 0.1,
        "max_tokens": 4096,
    },
    "tools": {
        "allowed": ["read_file", "write_file", "run_shell", "finish"],
        "shell_timeout": 60,
    },
    "guardrails": {
        "allowed_paths": ["./src", "./tests", "./demo", "./spec"],
        "command_rules": [
            {
                "pattern": r"^(ls|cat|pytest|flake8|mypy|python|pip|git status|git diff|echo|mkdir|touch)\b",
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
        ],
        "hitl": {"timeout": 30, "enabled": True},
        "sandbox": {"enabled": False, "memory_limit_mb": 512, "cpu_time_limit": 30},
    },
    "memory": {"db_path": "~/.harness/memory.db", "max_context_turns": 10},
}


class ConfigLoader:
    """Load and validate harness configuration from YAML files.

    Search order:
    1. User-specified path (--config or default "harness.yaml")
    2. ~/.harness/config.yaml
    3. Built-in package default (src/harness.yaml)
    4. Hardcoded fallback defaults
    """

    def load(self, path: str | None = None) -> dict:
        """Load config, searching multiple locations.

        Args:
            path: Optional explicit config path. If None, searches default locations.

        Returns:
            Validated config dict.

        Raises:
            ValueError: If a found config file is invalid.
        """
        search_paths = self._build_search_paths(path)

        for config_path in search_paths:
            resolved = Path(config_path).expanduser()
            if resolved.exists():
                return self._load_file(resolved)

        # No config file found — use built-in defaults
        return dict(_DEFAULT_CONFIG)

    def _build_search_paths(self, user_path: str | None) -> list[str]:
        """Build the ordered list of config paths to try."""
        paths = []
        if user_path:
            paths.append(user_path)
        else:
            paths.append("harness.yaml")
        paths.append(str(Path.home() / ".harness" / "config.yaml"))
        # Package-internal default (installed alongside the src package)
        pkg_dir = Path(__file__).resolve().parent.parent
        paths.append(str(pkg_dir / "harness.yaml"))
        return paths

    def _load_file(self, config_path: Path) -> dict:
        """Load and validate a single YAML config file."""
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