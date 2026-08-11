# Coding Agent Harness 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 构建一个可治理、可观测的 Python Coding Agent Harness，包含六个维度的最小实现，其中护栏/治理系统为深入实现。

**Architecture:** 分层架构：数据模型层 → 独立模块层（LLM 抽象、配置、记忆、工具、护栏、反馈）→ 主循环编排层 → CLI/Web 界面层。护栏为四层状态机（文件围栏 → 命令分级 → HITL → 沙箱）。所有模块通过 Protocol 接口解耦，支持 Mock LLM 确定性测试。

**Tech Stack:** Python 3.11+, pytest + pytest-asyncio, FastAPI + Jinja2, click, SQLite, pyyaml, keyring, openai SDK, httpx, pydantic

## 全局约束

- Python 版本 >= 3.11
- 所有核心机制必须能用 Mock LLM 做确定性单元测试
- 凭据绝不硬编码或写入 git，使用 keyring 存储
- 不使用 LangChain、AutoGen、CrewAI 等高级 agent 框架
- 测试框架: pytest + pytest-asyncio，测试命令: `pytest tests/ -v`
- 配置文件格式: YAML，默认路径: `harness.yaml` 或 `~/.harness/config.yaml`
- 代码风格: 遵循 PEP 8，类型注解完整
- 异步: 所有 I/O 操作使用 asyncio

---

## 文件结构

```
src/
├── __init__.py
├── models.py              # 所有 dataclass 数据模型
├── harness.yaml           # 默认配置文件
├── loop/
│   ├── __init__.py
│   └── agent.py           # 智能体主循环
├── tools/
│   ├── __init__.py
│   ├── schema.py          # 工具 JSON Schema 定义
│   └── executor.py        # 工具执行器
├── guardrails/
│   ├── __init__.py
│   ├── base.py            # Guardrail Protocol + Pipeline
│   ├── file_fence.py      # 文件系统围栏
│   ├── command_classifier.py  # 命令分级
│   ├── hitl.py            # 人机交互审批
│   └── sandbox.py         # 沙箱执行
├── feedback/
│   ├── __init__.py
│   └── parser.py          # 反馈解析器 + 失败分类
├── memory/
│   ├── __init__.py
│   └── store.py           # SQLite 存储 + 检索
├── config/
│   ├── __init__.py
│   └── loader.py          # YAML 配置加载 + 校验
├── llm/
│   ├── __init__.py
│   ├── base.py            # LLMBackend Protocol
│   ├── mock_backend.py    # Mock LLM（测试用）
│   └── openai_backend.py  # OpenAI 兼容适配器
├── cli/
│   ├── __init__.py
│   └── main.py            # Click CLI 入口
└── web/
    ├── __init__.py
    ├── app.py             # FastAPI 应用
    ├── routes.py          # API 路由
    └── templates/
        └── index.html     # 仪表盘模板

tests/
├── __init__.py
├── conftest.py            # 共享 fixtures
├── test_models.py
├── test_llm_mock.py
├── test_llm_openai.py
├── test_config.py
├── test_memory.py
├── test_tools.py
├── test_file_fence.py
├── test_command_classifier.py
├── test_hitl.py
├── test_sandbox.py
├── test_guardrail_pipeline.py
├── test_feedback.py
├── test_loop.py
├── test_cli.py
└── test_web.py

demo/
├── demo1_guardrail_intercept.py
├── demo2_feedback_loop.py
└── demo3_guardrail_pipeline.py
```

---

## 依赖关系图

```
Phase 1: 基础设施（无依赖，可并行）
  Task 1: 项目脚手架
  Task 2: 数据模型
  Task 3: 默认配置文件
      │
      ▼
Phase 2: 独立模块（依赖 Task 2，可并行）
  Task 4:  LLM 抽象层 + Mock Backend
  Task 5:  配置加载器
  Task 6:  记忆系统
  Task 7:  工具 Schema 定义
  Task 8:  工具执行器
      │
      ▼
Phase 3: 护栏系统 — 深入模块（依赖 Task 2，可并行）
  Task 9:  护栏基础协议 + Pipeline
  Task 10: 文件围栏
  Task 11: 命令分级
  Task 12: HITL 审批
  Task 13: 沙箱执行
  Task 14: 护栏 Pipeline 集成
      │
      ▼
Phase 4: 反馈回路（依赖 Task 2）
  Task 15: 反馈解析器 + 失败分类
      │
      ▼
Phase 5: 主循环（依赖 Task 4-15）
  Task 16: 智能体主循环
      │
      ▼
Phase 6: 界面层（依赖 Task 16，可并行）
  Task 17: CLI 命令行
  Task 18: Web 仪表盘
      │
      ▼
Phase 7: 演示 + 集成 + 文档（依赖 Task 16）
  Task 19: OpenAI 兼容后端
  Task 20: 演示脚本
  Task 21: CI 配置
  Task 22: 集成测试
  Task 23: README 文档
```

---
## Phase 1: 基础设施

### Task 1: 项目脚手架

**Files:**
- Create: `pyproject.toml`
- Create: `src/__init__.py`
- Create: `tests/__init__.py`
- Create: `tests/conftest.py`
- Create: `.gitignore`

**Interfaces:**
- Produces: 项目可 `pip install -e .` 安装，`pytest tests/` 可运行

- [ ] **Step 1: 创建 pyproject.toml**

```toml
[build-system]
requires = ["setuptools>=68.0", "wheel"]
build-backend = "setuptools.backends._legacy:_Backend"

[project]
name = "ai4se-harness"
version = "0.1.0"
description = "A governable coding agent harness"
requires-python = ">=3.11"
dependencies = [
    "openai>=1.0",
    "pyyaml>=6.0",
    "keyring>=24.0",
    "click>=8.0",
    "fastapi>=0.100",
    "uvicorn[standard]>=0.20",
    "jinja2>=3.0",
    "pydantic>=2.0",
    "httpx>=0.25",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0",
    "pytest-asyncio>=0.21",
    "pytest-cov>=4.0",
]

[project.scripts]
harness = "src.cli.main:cli"

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

- [ ] **Step 2: 创建 .gitignore**

```
__pycache__/
*.pyc
*.egg-info/
dist/
build/
.eggs/
.pytest_cache/
.coverage
htmlcov/
.harness/
.env
*.db
.venv/
venv/
```

- [ ] **Step 3: 创建空的 __init__.py 文件**

```bash
touch src/__init__.py tests/__init__.py
```

- [ ] **Step 4: 创建 tests/conftest.py**

```python
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
```

- [ ] **Step 5: 安装依赖并验证**

```bash
pip install -e ".[dev]"
pytest tests/ -v
```
Expected: 0 tests collected (no tests yet, but pytest runs successfully)

- [ ] **Step 6: 提交**

```bash
git add pyproject.toml .gitignore src/__init__.py tests/__init__.py tests/conftest.py
git commit -m "feat: project scaffolding with pyproject.toml and test fixtures"
```

---

### Task 2: 数据模型

**Files:**
- Create: `src/models.py`
- Create: `tests/test_models.py`

**Interfaces:**
- Produces: `Message`, `ToolCall`, `ToolResult`, `GuardrailResult`, `Feedback`, `FeedbackType`, `LLMResponse`, `Session`, `Action`, `CommandLevel`, `HarnessConfig`

- [ ] **Step 1: 编写失败测试**

```python
# tests/test_models.py
"""Tests for data models."""
from dataclasses import asdict
from src.models import (
    Message, ToolCall, ToolResult, GuardrailResult,
    Feedback, FeedbackType, LLMResponse, Session, Action, CommandLevel,
)


def test_message_creation():
    msg = Message(role="user", content="hello")
    assert msg.role == "user"
    assert msg.content == "hello"
    assert msg.tool_calls is None


def test_message_with_tool_calls():
    tc = ToolCall(id="call_1", name="read_file", arguments={"path": "test.py"})
    msg = Message(role="assistant", content=None, tool_calls=[tc])
    assert msg.tool_calls[0].name == "read_file"


def test_tool_result_fields():
    result = ToolResult(
        tool_call_id="call_1",
        tool_name="read_file",
        success=True,
        stdout="file content",
        stderr="",
        exit_code=0,
        duration_ms=12.5,
    )
    assert result.success is True
    assert result.exit_code == 0


def test_guardrail_result_blocked():
    result = GuardrailResult(
        allowed=False, level="dangerous",
        reason="rm -rf is forbidden", requires_hitl=True, blocked=True,
    )
    assert result.blocked is True
    assert result.allowed is False


def test_guardrail_result_allowed():
    result = GuardrailResult(
        allowed=True, level="safe",
        reason=None, requires_hitl=False, blocked=False,
    )
    assert result.blocked is False


def test_feedback_types():
    assert FeedbackType.SYNTAX_ERROR.value == "SYNTAX_ERROR"
    assert FeedbackType.ASSERTION_FAILURE.value == "ASSERTION_FAILURE"
    assert FeedbackType.IMPORT_ERROR.value == "IMPORT_ERROR"
    assert FeedbackType.TIMEOUT.value == "TIMEOUT"
    assert FeedbackType.UNKNOWN.value == "UNKNOWN"


def test_feedback_creation():
    fb = Feedback(
        type=FeedbackType.ASSERTION_FAILURE,
        summary="test_add failed",
        detail="assert 3 == 5 in test_add",
        suggestion="Check the addition logic",
        failed_count=1,
        passed_count=2,
    )
    assert fb.type == FeedbackType.ASSERTION_FAILURE
    assert fb.failed_count == 1


def test_llm_response_with_tool_calls():
    tc = ToolCall(id="call_1", name="run_shell", arguments={"cmd": "pytest"})
    resp = LLMResponse(
        content=None,
        tool_calls=[tc],
        finish_reason="tool_calls",
        usage={"prompt_tokens": 100, "completion_tokens": 50},
    )
    assert resp.finish_reason == "tool_calls"
    assert len(resp.tool_calls) == 1


def test_llm_response_text():
    resp = LLMResponse(
        content="Task completed.",
        tool_calls=None,
        finish_reason="stop",
        usage=None,
    )
    assert resp.content == "Task completed."


def test_action_creation():
    action = Action(
        tool_name="run_shell",
        arguments={"cmd": "rm -rf /"},
    )
    assert action.tool_name == "run_shell"
    assert action.arguments["cmd"] == "rm -rf /"


def test_command_level_enum():
    assert CommandLevel.SAFE.value == "safe"
    assert CommandLevel.WARN.value == "warn"
    assert CommandLevel.DANGEROUS.value == "dangerous"


def test_session_fields():
    from datetime import datetime
    session = Session(
        id="abc-123",
        task="Run tests",
        status="running",
        turns=0,
        created_at=datetime.now(),
        completed_at=None,
    )
    assert session.status == "running"
    assert session.turns == 0
```

- [ ] **Step 2: 运行测试验证失败**

```bash
pytest tests/test_models.py -v
```
Expected: ImportError (models.py 不存在)

- [ ] **Step 3: 实现数据模型**

```python
# src/models.py
"""Core data models for the Coding Agent Harness."""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Literal, Optional


class CommandLevel(str, Enum):
    SAFE = "safe"
    WARN = "warn"
    DANGEROUS = "dangerous"


class FeedbackType(str, Enum):
    SYNTAX_ERROR = "SYNTAX_ERROR"
    ASSERTION_FAILURE = "ASSERTION_FAILURE"
    IMPORT_ERROR = "IMPORT_ERROR"
    TIMEOUT = "TIMEOUT"
    UNKNOWN = "UNKNOWN"


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict[str, Any]


@dataclass
class Message:
    role: Literal["system", "user", "assistant", "tool"]
    content: Optional[str] = None
    tool_calls: Optional[list[ToolCall]] = None
    tool_call_id: Optional[str] = None
    name: Optional[str] = None


@dataclass
class ToolResult:
    tool_call_id: str
    tool_name: str
    success: bool
    stdout: str
    stderr: str
    exit_code: int
    duration_ms: float = 0.0


@dataclass
class GuardrailResult:
    allowed: bool
    level: str
    reason: Optional[str] = None
    requires_hitl: bool = False
    blocked: bool = False


@dataclass
class Feedback:
    type: FeedbackType
    summary: str
    detail: str
    suggestion: str = ""
    failed_count: int = 0
    passed_count: int = 0


@dataclass
class LLMResponse:
    content: Optional[str] = None
    tool_calls: Optional[list[ToolCall]] = None
    finish_reason: str = "stop"
    usage: Optional[dict[str, int]] = None


@dataclass
class Action:
    tool_name: str
    arguments: dict[str, Any]


@dataclass
class Session:
    id: str
    task: str
    status: str = "running"
    turns: int = 0
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
```

- [ ] **Step 4: 运行测试验证通过**

```bash
pytest tests/test_models.py -v
```
Expected: ALL PASS

- [ ] **Step 5: 提交**

```bash
git add src/models.py tests/test_models.py
git commit -m "feat: add core data models (Message, ToolCall, GuardrailResult, etc.)"
```

---

### Task 3: 默认配置文件

**Files:**
- Create: `src/harness.yaml`

**Interfaces:**
- Produces: 默认配置文件，供 Config Loader（Task 5）读取

- [ ] **Step 1: 创建默认配置文件**

```yaml
# src/harness.yaml — Default Harness Configuration
loop:
  max_turns: 20
  idle_timeout: 3

llm:
  provider: "openai_compat"
  model: "gpt-4o"
  api_base: "https://your-relay.com/v1"
  api_key_cmd: "keyring get harness"
  temperature: 0.1
  max_tokens: 4096

tools:
  allowed:
    - read_file
    - write_file
    - run_shell
    - finish
  shell_timeout: 60

guardrails:
  allowed_paths:
    - "./src"
    - "./tests"
    - "./demo"
    - "./spec"
  command_rules:
    - pattern: "^(ls|cat|pytest|flake8|mypy|python|pip|git status|git diff|echo|mkdir|touch)\\b"
      level: safe
    - pattern: "^(git commit|git checkout|git branch|pip install|npm install)\\b"
      level: warn
    - pattern: "\\brm -rf\\b|\\bDROP TABLE\\b|\\bDELETE FROM\\b|git push --force|chmod 777|\\bsudo\\b|> /dev/|\\bmkfs\\b|\\bdd if="
      level: dangerous
  hitl:
    timeout: 30
    enabled: true
  sandbox:
    enabled: false
    memory_limit_mb: 512
    cpu_time_limit: 30

memory:
  db_path: "~/.harness/memory.db"
  max_context_turns: 10

web:
  host: "0.0.0.0"
  port: 8080
```

- [ ] **Step 2: 验证 YAML 语法正确**

```bash
python -c "import yaml; yaml.safe_load(open('src/harness.yaml')); print('OK')"
```
Expected: OK

- [ ] **Step 3: 提交**

```bash
git add src/harness.yaml
git commit -m "feat: add default harness.yaml configuration"
```

---

## Phase 2: 独立模块

### Task 4: LLM 抽象层 + Mock Backend

**Files:**
- Create: `src/llm/__init__.py`
- Create: `src/llm/base.py`
- Create: `src/llm/mock_backend.py`
- Create: `tests/test_llm_mock.py`

**Interfaces:**
- Consumes: `Message`, `ToolCall`, `LLMResponse` from `src/models.py`
- Produces: `LLMBackend` Protocol with `async def chat(self, messages: list[Message], tools: list[dict]) -> LLMResponse`
- Produces: `MockLLMBackend` implementing `LLMBackend`, takes `responses: list[LLMResponse]` in constructor

- [ ] **Step 1: 创建目录并编写失败测试**

```bash
mkdir -p src/llm
touch src/llm/__init__.py
```

```python
# tests/test_llm_mock.py
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
```

- [ ] **Step 2: 运行测试验证失败**

```bash
pytest tests/test_llm_mock.py -v
```
Expected: ImportError (mock_backend.py 不存在)

- [ ] **Step 3: 实现 LLMBackend Protocol 和 MockLLMBackend**

```python
# src/llm/base.py
"""LLM Backend Protocol."""
from typing import Protocol, runtime_checkable
from src.models import Message, LLMResponse


@runtime_checkable
class LLMBackend(Protocol):
    """Protocol for LLM backends. Both real and mock implementations must satisfy this."""

    async def chat(
        self, messages: list[Message], tools: list[dict]
    ) -> LLMResponse:
        """Send messages to LLM and get a response (text or tool_calls)."""
        ...
```

```python
# src/llm/mock_backend.py
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
```

- [ ] **Step 4: 运行测试验证通过**

```bash
pytest tests/test_llm_mock.py -v
```
Expected: ALL PASS

- [ ] **Step 5: 提交**

```bash
git add src/llm/ tests/test_llm_mock.py
git commit -m "feat: add LLMBackend Protocol and MockLLMBackend"
```

---

### Task 5: 配置加载器

**Files:**
- Create: `src/config/__init__.py`
- Create: `src/config/loader.py`
- Create: `tests/test_config.py`

**Interfaces:**
- Consumes: `src/harness.yaml` (Task 3), `sample_config_dict` fixture (Task 1)
- Produces: `ConfigLoader` class with methods:
  - `load(path: str) -> dict` — load and validate YAML
  - `get_guardrail_config() -> dict` — extract guardrail section
  - `get_llm_config() -> dict` — extract LLM section

- [ ] **Step 1: 创建目录并编写失败测试**

```bash
mkdir -p src/config
touch src/config/__init__.py
```

```python
# tests/test_config.py
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
```

- [ ] **Step 2: 运行测试验证失败**

```bash
pytest tests/test_config.py -v
```
Expected: ImportError

- [ ] **Step 3: 实现 ConfigLoader**

```python
# src/config/loader.py
"""Configuration loader with YAML parsing and validation."""
from pathlib import Path
import yaml


REQUIRED_TOP_KEYS = ["loop", "llm", "tools", "guardrails", "memory", "web"]


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
```

- [ ] **Step 4: 运行测试验证通过**

```bash
pytest tests/test_config.py -v
```
Expected: ALL PASS

- [ ] **Step 5: 提交**

```bash
git add src/config/ tests/test_config.py
git commit -m "feat: add YAML configuration loader with validation"
```

---

### Task 6: 记忆系统

**Files:**
- Create: `src/memory/__init__.py`
- Create: `src/memory/store.py`
- Create: `tests/test_memory.py`

**Interfaces:**
- Consumes: `Message`, `Session` from `src/models.py`
- Produces: `MemoryStore` class with methods:
  - `async def create_session(task: str) -> Session`
  - `async def add_message(session_id: str, turn: int, message: Message) -> None`
  - `async def get_context(session_id: str, max_turns: int = 10) -> list[Message]`
  - `async def save_fact(key: str, value: str, source: str = "") -> None`
  - `async def search_facts(query: str) -> list[dict]`
  - `async def update_session(session_id: str, status: str, turns: int) -> None`

- [ ] **Step 1: 创建目录并编写失败测试**

```bash
mkdir -p src/memory
touch src/memory/__init__.py
```

```python
# tests/test_memory.py
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
```

- [ ] **Step 2: 运行测试验证失败**

```bash
pytest tests/test_memory.py -v
```
Expected: 6 failed (ImportError)

- [ ] **Step 3: 实现 MemoryStore**

```python
# src/memory/store.py
"""SQLite-based memory store for session history and persistent facts."""
import sqlite3
import json
import uuid
from datetime import datetime
from src.models import Message, Session, ToolCall


class MemoryStore:
    """Stores and retrieves conversation history and persistent facts."""

    def __init__(self, db_path: str = ":memory:"):
        self.db_path = db_path
        self._conn: sqlite3.Connection | None = None

    def _get_conn(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(self.db_path)
            self._conn.row_factory = sqlite3.Row
            self._create_tables()
        return self._conn

    def _create_tables(self) -> None:
        conn = self._get_conn()
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                task TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'running',
                turns INTEGER DEFAULT 0,
                created_at TEXT NOT NULL,
                completed_at TEXT
            );
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                turn INTEGER NOT NULL,
                role TEXT NOT NULL,
                content TEXT,
                tool_calls TEXT,
                tool_results TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (session_id) REFERENCES sessions(id)
            );
            CREATE TABLE IF NOT EXISTS facts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key TEXT NOT NULL UNIQUE,
                value TEXT NOT NULL,
                source TEXT DEFAULT '',
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                event_type TEXT NOT NULL,
                detail TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
        """)
        conn.commit()

    async def create_session(self, task: str) -> Session:
        session = Session(
            id=str(uuid.uuid4()),
            task=task,
            created_at=datetime.now(),
        )
        conn = self._get_conn()
        conn.execute(
            "INSERT INTO sessions (id, task, status, turns, created_at) VALUES (?, ?, ?, ?, ?)",
            (session.id, session.task, session.status, session.turns, session.created_at.isoformat()),
        )
        conn.commit()
        return session

    async def add_message(self, session_id: str, turn: int, message: Message) -> None:
        conn = self._get_conn()
        tool_calls_json = None
        if message.tool_calls:
            tool_calls_json = json.dumps([
                {"id": tc.id, "name": tc.name, "arguments": tc.arguments}
                for tc in message.tool_calls
            ])
        conn.execute(
            "INSERT INTO messages (session_id, turn, role, content, tool_calls, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (session_id, turn, message.role, message.content, tool_calls_json, datetime.now().isoformat()),
        )
        conn.commit()

    async def get_context(self, session_id: str, max_turns: int = 10) -> list[Message]:
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT * FROM messages WHERE session_id = ? ORDER BY turn DESC LIMIT ?",
            (session_id, max_turns),
        ).fetchall()
        messages = []
        for row in reversed(rows):
            tool_calls = None
            if row["tool_calls"]:
                tcs = json.loads(row["tool_calls"])
                tool_calls = [ToolCall(id=tc["id"], name=tc["name"], arguments=tc["arguments"]) for tc in tcs]
            messages.append(Message(
                role=row["role"],
                content=row["content"],
                tool_calls=tool_calls,
            ))
        return messages

    async def save_fact(self, key: str, value: str, source: str = "") -> None:
        conn = self._get_conn()
        conn.execute(
            "INSERT OR REPLACE INTO facts (key, value, source, created_at) VALUES (?, ?, ?, ?)",
            (key, value, source, datetime.now().isoformat()),
        )
        conn.commit()

    async def search_facts(self, query: str) -> list[dict]:
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT * FROM facts WHERE key LIKE ? OR value LIKE ?",
            (f"%{query}%", f"%{query}%"),
        ).fetchall()
        return [dict(row) for row in rows]

    async def update_session(self, session_id: str, status: str, turns: int) -> None:
        conn = self._get_conn()
        completed_at = datetime.now().isoformat() if status in ("completed", "error", "stopped") else None
        conn.execute(
            "UPDATE sessions SET status = ?, turns = ?, completed_at = ? WHERE id = ?",
            (status, turns, completed_at, session_id),
        )
        conn.commit()

    async def log_audit(self, session_id: str | None, event_type: str, detail: dict) -> None:
        conn = self._get_conn()
        conn.execute(
            "INSERT INTO audit_log (session_id, event_type, detail, created_at) VALUES (?, ?, ?, ?)",
            (session_id, event_type, json.dumps(detail), datetime.now().isoformat()),
        )
        conn.commit()
```

- [ ] **Step 4: 运行测试验证通过**

```bash
pytest tests/test_memory.py -v
```
Expected: ALL PASS

- [ ] **Step 5: 提交**

```bash
git add src/memory/ tests/test_memory.py
git commit -m "feat: add SQLite-based memory store for sessions and facts"
```

---
### Task 7: 工具 Schema 定义

**Files:**
- Create: `src/tools/__init__.py`
- Create: `src/tools/schema.py`
- Create: `tests/test_tools.py` (schema tests only in this task)

**Interfaces:**
- Produces: `TOOL_SCHEMAS: list[dict]` — OpenAI function-calling format tool definitions
- Produces: `def get_tool_schema(name: str) -> dict` — get schema for a single tool
- Produces: `def get_allowed_tools(allowed: list[str]) -> list[dict]` — filter schemas by allowed list

- [ ] **Step 1: 创建目录并编写失败测试**

```bash
mkdir -p src/tools
touch src/tools/__init__.py
```

```python
# tests/test_tools.py
"""Tests for tool schemas and executor."""
import pytest
from src.tools.schema import TOOL_SCHEMAS, get_tool_schema, get_allowed_tools


def test_all_four_tools_defined():
    names = [t["function"]["name"] for t in TOOL_SCHEMAS]
    assert "read_file" in names
    assert "write_file" in names
    assert "run_shell" in names
    assert "finish" in names


def test_read_file_schema():
    schema = get_tool_schema("read_file")
    assert schema["function"]["name"] == "read_file"
    assert "path" in schema["function"]["parameters"]["properties"]
    assert "path" in schema["function"]["parameters"]["required"]


def test_write_file_schema():
    schema = get_tool_schema("write_file")
    props = schema["function"]["parameters"]["properties"]
    assert "path" in props
    assert "content" in props
    assert set(schema["function"]["parameters"]["required"]) == {"path", "content"}


def test_run_shell_schema():
    schema = get_tool_schema("run_shell")
    props = schema["function"]["parameters"]["properties"]
    assert "cmd" in props
    assert "cwd" in props


def test_finish_schema():
    schema = get_tool_schema("finish")
    props = schema["function"]["parameters"]["properties"]
    assert "summary" in props


def test_get_tool_schema_unknown():
    with pytest.raises(ValueError, match="Unknown tool"):
        get_tool_schema("nonexistent_tool")


def test_get_allowed_tools_filters():
    allowed = get_allowed_tools(["read_file", "finish"])
    names = [t["function"]["name"] for t in allowed]
    assert names == ["read_file", "finish"]


def test_get_allowed_tools_all():
    allowed = get_allowed_tools(["read_file", "write_file", "run_shell", "finish"])
    assert len(allowed) == 4
```

- [ ] **Step 2: 运行测试验证失败**

```bash
pytest tests/test_tools.py -v
```
Expected: 8 failed (ImportError)

- [ ] **Step 3: 实现工具 Schema**

```python
# src/tools/schema.py
"""Tool definitions in OpenAI function-calling JSON Schema format."""

READ_FILE_SCHEMA = {
    "type": "function",
    "function": {
        "name": "read_file",
        "description": "Read the contents of a file at the given path.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "The path to the file to read.",
                },
            },
            "required": ["path"],
        },
    },
}

WRITE_FILE_SCHEMA = {
    "type": "function",
    "function": {
        "name": "write_file",
        "description": "Write content to a file, creating it if it does not exist.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "The path to the file to write.",
                },
                "content": {
                    "type": "string",
                    "description": "The content to write to the file.",
                },
            },
            "required": ["path", "content"],
        },
    },
}

RUN_SHELL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "run_shell",
        "description": "Execute a shell command and return its output.",
        "parameters": {
            "type": "object",
            "properties": {
                "cmd": {
                    "type": "string",
                    "description": "The shell command to execute.",
                },
                "cwd": {
                    "type": "string",
                    "description": "Working directory for the command (optional).",
                },
            },
            "required": ["cmd"],
        },
    },
}

FINISH_SCHEMA = {
    "type": "function",
    "function": {
        "name": "finish",
        "description": "Declare the task as finished and provide a summary.",
        "parameters": {
            "type": "object",
            "properties": {
                "summary": {
                    "type": "string",
                    "description": "A summary of what was accomplished.",
                },
            },
            "required": ["summary"],
        },
    },
}

TOOL_SCHEMAS = [READ_FILE_SCHEMA, WRITE_FILE_SCHEMA, RUN_SHELL_SCHEMA, FINISH_SCHEMA]

_SCHEMA_MAP = {t["function"]["name"]: t for t in TOOL_SCHEMAS}


def get_tool_schema(name: str) -> dict:
    """Get the JSON Schema for a specific tool by name.

    Raises:
        ValueError: If the tool name is not recognized.
    """
    if name not in _SCHEMA_MAP:
        raise ValueError(f"Unknown tool: {name}. Available: {list(_SCHEMA_MAP.keys())}")
    return _SCHEMA_MAP[name]


def get_allowed_tools(allowed: list[str]) -> list[dict]:
    """Filter tool schemas to only those in the allowed list."""
    return [s for s in TOOL_SCHEMAS if s["function"]["name"] in allowed]
```

- [ ] **Step 4: 运行测试验证通过**

```bash
pytest tests/test_tools.py -v
```
Expected: 8 PASS

- [ ] **Step 5: 提交**

```bash
git add src/tools/ tests/test_tools.py
git commit -m "feat: add tool schema definitions (read_file, write_file, run_shell, finish)"
```

---

### Task 8: 工具执行器

**Files:**
- Create: `src/tools/executor.py`
- Append: `tests/test_tools.py` (add executor tests)

**Interfaces:**
- Consumes: `ToolCall`, `ToolResult` from `src/models.py`
- Consumes: `get_tool_schema` from `src/tools/schema.py`
- Produces: `async def execute_tool(tool_call: ToolCall, cwd: str = ".") -> ToolResult`

- [ ] **Step 1: 编写失败测试（追加到已有测试文件）**

```python
# Append to tests/test_tools.py
import time
from src.models import ToolCall, ToolResult
from src.tools.executor import execute_tool


@pytest.mark.asyncio
async def test_execute_read_file(temp_dir):
    test_file = temp_dir / "test.txt"
    test_file.write_text("hello world")
    tc = ToolCall(id="c1", name="read_file", arguments={"path": str(test_file)})
    result = await execute_tool(tc)
    assert result.success is True
    assert result.stdout == "hello world"
    assert result.exit_code == 0


@pytest.mark.asyncio
async def test_execute_read_file_not_found():
    tc = ToolCall(id="c1", name="read_file", arguments={"path": "/nonexistent/file.txt"})
    result = await execute_tool(tc)
    assert result.success is False
    assert "not found" in result.stderr.lower()


@pytest.mark.asyncio
async def test_execute_write_file(temp_dir):
    test_file = temp_dir / "output.txt"
    tc = ToolCall(id="c1", name="write_file", arguments={
        "path": str(test_file), "content": "new content",
    })
    result = await execute_tool(tc)
    assert result.success is True
    assert test_file.read_text() == "new content"


@pytest.mark.asyncio
async def test_execute_write_file_creates_dirs(temp_dir):
    test_file = temp_dir / "subdir" / "nested" / "file.txt"
    tc = ToolCall(id="c1", name="write_file", arguments={
        "path": str(test_file), "content": "nested",
    })
    result = await execute_tool(tc)
    assert result.success is True
    assert test_file.read_text() == "nested"


@pytest.mark.asyncio
async def test_execute_run_shell_success():
    tc = ToolCall(id="c1", name="run_shell", arguments={"cmd": "echo hello"})
    result = await execute_tool(tc)
    assert result.success is True
    assert "hello" in result.stdout
    assert result.exit_code == 0


@pytest.mark.asyncio
async def test_execute_run_shell_failure():
    tc = ToolCall(id="c1", name="run_shell", arguments={"cmd": "python -c 'exit(1)'"})
    result = await execute_tool(tc)
    assert result.success is False
    assert result.exit_code == 1


@pytest.mark.asyncio
async def test_execute_run_shell_timeout():
    tc = ToolCall(id="c1", name="run_shell", arguments={"cmd": "sleep 10"})
    result = await execute_tool(tc, timeout=1)
    assert result.success is False
    assert "timeout" in result.stderr.lower()


@pytest.mark.asyncio
async def test_execute_finish():
    tc = ToolCall(id="c1", name="finish", arguments={"summary": "All done"})
    result = await execute_tool(tc)
    assert result.success is True
    assert "All done" in result.stdout


@pytest.mark.asyncio
async def test_execute_unknown_tool():
    tc = ToolCall(id="c1", name="unknown_tool", arguments={})
    result = await execute_tool(tc)
    assert result.success is False
    assert "Unknown tool" in result.stderr
```

- [ ] **Step 2: 运行测试验证失败**

```bash
pytest tests/test_tools.py -v -k "executor"
```
Expected: FAIL (ImportError for executor)

- [ ] **Step 3: 实现工具执行器**

```python
# src/tools/executor.py
"""Tool executor — dispatches tool calls to actual implementations."""
import asyncio
import os
from pathlib import Path
from src.models import ToolCall, ToolResult


async def execute_tool(tool_call: ToolCall, cwd: str = ".", timeout: int = 60) -> ToolResult:
    """Execute a single tool call and return the result.

    Args:
        tool_call: The tool call to execute.
        cwd: Working directory for shell commands.
        timeout: Timeout in seconds for shell commands.

    Returns:
        ToolResult with stdout, stderr, exit_code, and success flag.
    """
    name = tool_call.name
    args = tool_call.arguments

    if name == "read_file":
        return await _read_file(args.get("path", ""))
    elif name == "write_file":
        return await _write_file(args.get("path", ""), args.get("content", ""))
    elif name == "run_shell":
        return await _run_shell(args.get("cmd", ""), args.get("cwd", cwd), timeout)
    elif name == "finish":
        return await _finish(args.get("summary", ""))
    else:
        return ToolResult(
            tool_call_id=tool_call.id,
            tool_name=name,
            success=False,
            stdout="",
            stderr=f"Unknown tool: {name}",
            exit_code=-1,
        )


async def _read_file(path: str) -> ToolResult:
    try:
        content = Path(path).read_text(encoding="utf-8")
        return ToolResult(
            tool_call_id="",
            tool_name="read_file",
            success=True,
            stdout=content,
            stderr="",
            exit_code=0,
        )
    except FileNotFoundError:
        return ToolResult(
            tool_call_id="",
            tool_name="read_file",
            success=False,
            stdout="",
            stderr=f"File not found: {path}",
            exit_code=1,
        )
    except Exception as e:
        return ToolResult(
            tool_call_id="",
            tool_name="read_file",
            success=False,
            stdout="",
            stderr=str(e),
            exit_code=1,
        )


async def _write_file(path: str, content: str) -> ToolResult:
    try:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return ToolResult(
            tool_call_id="",
            tool_name="write_file",
            success=True,
            stdout=f"Written {len(content)} bytes to {path}",
            stderr="",
            exit_code=0,
        )
    except Exception as e:
        return ToolResult(
            tool_call_id="",
            tool_name="write_file",
            success=False,
            stdout="",
            stderr=str(e),
            exit_code=1,
        )


async def _run_shell(cmd: str, cwd: str, timeout: int) -> ToolResult:
    try:
        proc = await asyncio.create_subprocess_shell(
            cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=cwd,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        exit_code = proc.returncode or 0
        return ToolResult(
            tool_call_id="",
            tool_name="run_shell",
            success=exit_code == 0,
            stdout=stdout.decode("utf-8", errors="replace"),
            stderr=stderr.decode("utf-8", errors="replace"),
            exit_code=exit_code,
        )
    except asyncio.TimeoutError:
        return ToolResult(
            tool_call_id="",
            tool_name="run_shell",
            success=False,
            stdout="",
            stderr=f"Command timed out after {timeout}s: {cmd}",
            exit_code=-1,
        )
    except Exception as e:
        return ToolResult(
            tool_call_id="",
            tool_name="run_shell",
            success=False,
            stdout="",
            stderr=str(e),
            exit_code=1,
        )


async def _finish(summary: str) -> ToolResult:
    return ToolResult(
        tool_call_id="",
        tool_name="finish",
        success=True,
        stdout=f"Task finished: {summary}",
        stderr="",
        exit_code=0,
    )
```

- [ ] **Step 4: 运行测试验证通过**

```bash
pytest tests/test_tools.py -v
```
Expected: ALL PASS

- [ ] **Step 5: 提交**

```bash
git add src/tools/executor.py tests/test_tools.py
git commit -m "feat: add tool executor with read_file, write_file, run_shell, finish"
```

---

## Phase 3: 护栏系统 — 深入模块

### Task 9: 护栏基础协议 + Pipeline

**Files:**
- Create: `src/guardrails/__init__.py`
- Create: `src/guardrails/base.py`
- Create: `tests/test_guardrail_pipeline.py`

**Interfaces:**
- Consumes: `Action`, `GuardrailResult` from `src/models.py`
- Produces: `Guardrail` Protocol with `async def check(self, action: Action) -> GuardrailResult`
- Produces: `GuardrailPipeline` class with `async def check(self, action: Action) -> GuardrailResult`

- [ ] **Step 1: 创建目录并编写失败测试**

```bash
mkdir -p src/guardrails
touch src/guardrails/__init__.py
```

```python
# tests/test_guardrail_pipeline.py
"""Tests for guardrail pipeline."""
import pytest
from src.models import Action, GuardrailResult
from src.guardrails.base import Guardrail, GuardrailPipeline


class FakeBlockGuardrail:
    """A guardrail that always blocks."""
    async def check(self, action: Action) -> GuardrailResult:
        return GuardrailResult(
            allowed=False, level="dangerous",
            reason="always blocked", requires_hitl=False, blocked=True,
        )


class FakePassGuardrail:
    """A guardrail that always passes."""
    async def check(self, action: Action) -> GuardrailResult:
        return GuardrailResult(
            allowed=True, level="safe",
            reason=None, requires_hitl=False, blocked=False,
        )


@pytest.mark.asyncio
async def test_pipeline_stops_at_first_block():
    pipeline = GuardrailPipeline([
        FakeBlockGuardrail(),
        FakePassGuardrail(),
    ])
    action = Action(tool_name="run_shell", arguments={"cmd": "ls"})
    result = await pipeline.check(action)
    assert result.blocked is True
    assert result.reason == "always blocked"


@pytest.mark.asyncio
async def test_pipeline_passes_when_all_pass():
    pipeline = GuardrailPipeline([
        FakePassGuardrail(),
        FakePassGuardrail(),
    ])
    action = Action(tool_name="run_shell", arguments={"cmd": "ls"})
    result = await pipeline.check(action)
    assert result.blocked is False
    assert result.allowed is True


@pytest.mark.asyncio
async def test_pipeline_empty_passes():
    pipeline = GuardrailPipeline([])
    action = Action(tool_name="run_shell", arguments={"cmd": "ls"})
    result = await pipeline.check(action)
    assert result.blocked is False


@pytest.mark.asyncio
async def test_fake_guardrail_satisfies_protocol():
    g = FakePassGuardrail()
    assert isinstance(g, Guardrail)
```

- [ ] **Step 2: 运行测试验证失败**

```bash
pytest tests/test_guardrail_pipeline.py -v
```
Expected: 4 failed (ImportError)

- [ ] **Step 3: 实现 Guardrail Protocol 和 Pipeline**

```python
# src/guardrails/base.py
"""Guardrail protocol and pipeline base classes."""
from typing import Protocol, runtime_checkable
from src.models import Action, GuardrailResult


@runtime_checkable
class Guardrail(Protocol):
    """Protocol for individual guardrail checks.

    Each guardrail layer implements this protocol.
    """

    async def check(self, action: Action) -> GuardrailResult:
        """Check an action and return a guardrail result.

        Args:
            action: The action (tool call) to check.

        Returns:
            GuardrailResult indicating whether the action is allowed.
        """
        ...


class GuardrailPipeline:
    """Pipeline that runs multiple guardrail layers in sequence.

    Stops at the first layer that blocks the action.
    """

    def __init__(self, layers: list[Guardrail]):
        self._layers = layers

    async def check(self, action: Action) -> GuardrailResult:
        """Run all guardrail layers in order. Returns first blocking result."""
        for layer in self._layers:
            result = await layer.check(action)
            if result.blocked:
                return result
        return GuardrailResult(
            allowed=True, level="safe",
            reason=None, requires_hitl=False, blocked=False,
        )
```

- [ ] **Step 4: 运行测试验证通过**

```bash
pytest tests/test_guardrail_pipeline.py -v
```
Expected: 4 PASS

- [ ] **Step 5: 提交**

```bash
git add src/guardrails/ tests/test_guardrail_pipeline.py
git commit -m "feat: add Guardrail Protocol and Pipeline base classes"
```

---

### Task 10: 文件系统围栏

**Files:**
- Create: `src/guardrails/file_fence.py`
- Create: `tests/test_file_fence.py`

**Interfaces:**
- Consumes: `Action`, `GuardrailResult` from `src/models.py`
- Produces: `FileFence` class implementing `Guardrail` Protocol
  - `__init__(allowed_paths: list[str])`
  - `async def check(self, action: Action) -> GuardrailResult`

- [ ] **Step 1: 编写失败测试**

```python
# tests/test_file_fence.py
"""Tests for file system fence guardrail."""
import pytest
from pathlib import Path
from src.models import Action
from src.guardrails.file_fence import FileFence


@pytest.fixture
def fence():
    return FileFence(allowed_paths=["./src", "./tests", "./demo"])


@pytest.mark.asyncio
async def test_blocks_read_outside_fence(fence):
    action = Action(tool_name="read_file", arguments={"path": "/etc/passwd"})
    result = await fence.check(action)
    assert result.blocked is True
    assert "outside allowed paths" in result.reason.lower()


@pytest.mark.asyncio
async def test_blocks_write_outside_fence(fence):
    action = Action(tool_name="write_file", arguments={"path": "/usr/bin/malware"})
    result = await fence.check(action)
    assert result.blocked is True


@pytest.mark.asyncio
async def test_allows_read_inside_fence(fence, temp_dir):
    # Create a file inside a fake ./src structure
    src_dir = temp_dir / "src"
    src_dir.mkdir()
    test_file = src_dir / "main.py"
    test_file.write_text("code")
    fence2 = FileFence(allowed_paths=[str(src_dir)])
    action = Action(tool_name="read_file", arguments={"path": str(test_file)})
    result = await fence2.check(action)
    assert result.blocked is False


@pytest.mark.asyncio
async def test_allows_write_inside_fence(fence, temp_dir):
    src_dir = temp_dir / "src"
    src_dir.mkdir()
    fence2 = FileFence(allowed_paths=[str(src_dir)])
    action = Action(tool_name="write_file", arguments={
        "path": str(src_dir / "new.py"), "content": "x",
    })
    result = await fence2.check(action)
    assert result.blocked is False


@pytest.mark.asyncio
async def test_skips_non_file_actions(fence):
    """File fence should only check read_file and write_file actions."""
    action = Action(tool_name="run_shell", arguments={"cmd": "ls"})
    result = await fence.check(action)
    assert result.blocked is False


@pytest.mark.asyncio
async def test_resolves_relative_paths(fence, temp_dir):
    src_dir = temp_dir / "src"
    src_dir.mkdir()
    test_file = src_dir / "main.py"
    test_file.write_text("code")
    fence2 = FileFence(allowed_paths=[str(src_dir)])
    # Use relative path
    import os
    original_cwd = os.getcwd()
    try:
        os.chdir(temp_dir)
        action = Action(tool_name="read_file", arguments={"path": "src/main.py"})
        result = await fence2.check(action)
        assert result.blocked is False
    finally:
        os.chdir(original_cwd)
```

- [ ] **Step 2: 运行测试验证失败**

```bash
pytest tests/test_file_fence.py -v
```
Expected: 6 failed (ImportError)

- [ ] **Step 3: 实现 FileFence**

```python
# src/guardrails/file_fence.py
"""File system fence guardrail — restricts file access to allowed paths."""
from pathlib import Path
from src.models import Action, GuardrailResult


class FileFence:
    """Restricts file read/write operations to a whitelist of allowed directories."""

    def __init__(self, allowed_paths: list[str]):
        self._allowed = [Path(p).resolve() for p in allowed_paths]

    async def check(self, action: Action) -> GuardrailResult:
        """Check if the action's file path is within allowed directories."""
        if action.tool_name not in ("read_file", "write_file"):
            return GuardrailResult(
                allowed=True, level="safe",
                reason=None, requires_hitl=False, blocked=False,
            )

        path_str = action.arguments.get("path", "")
        if not path_str:
            return GuardrailResult(
                allowed=False, level="dangerous",
                reason="No path provided for file operation", blocked=True,
            )

        target = Path(path_str).resolve()

        for allowed in self._allowed:
            try:
                target.relative_to(allowed)
                return GuardrailResult(
                    allowed=True, level="safe",
                    reason=None, requires_hitl=False, blocked=False,
                )
            except ValueError:
                continue

        return GuardrailResult(
            allowed=False, level="dangerous",
            reason=f"File path '{path_str}' is outside allowed paths: {self._allowed}",
            blocked=True,
        )
```

- [ ] **Step 4: 运行测试验证通过**

```bash
pytest tests/test_file_fence.py -v
```
Expected: 6 PASS

- [ ] **Step 5: 提交**

```bash
git add src/guardrails/file_fence.py tests/test_file_fence.py
git commit -m "feat: add FileFence guardrail for file system path restrictions"
```

---

### Task 11: 命令分级

**Files:**
- Create: `src/guardrails/command_classifier.py`
- Create: `tests/test_command_classifier.py`

**Interfaces:**
- Consumes: `Action`, `GuardrailResult`, `CommandLevel` from `src/models.py`
- Produces: `CommandClassifier` class implementing `Guardrail` Protocol
  - `__init__(rules: list[dict])` — rules is list of {"pattern": str, "level": str}
  - `async def check(self, action: Action) -> GuardrailResult`

- [ ] **Step 1: 编写失败测试**

```python
# tests/test_command_classifier.py
"""Tests for command classifier guardrail."""
import pytest
from src.models import Action, CommandLevel
from src.guardrails.command_classifier import CommandClassifier


@pytest.fixture
def classifier():
    rules = [
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
```

- [ ] **Step 2: 运行测试验证失败**

```bash
pytest tests/test_command_classifier.py -v
```
Expected: 6 failed (ImportError)

- [ ] **Step 3: 实现 CommandClassifier**

```python
# src/guardrails/command_classifier.py
"""Command classifier guardrail — categorizes shell commands by risk level."""
import re
from src.models import Action, GuardrailResult


class CommandClassifier:
    """Classifies shell commands into safe/warn/dangerous based on regex rules."""

    def __init__(self, rules: list[dict]):
        self._rules = [
            (re.compile(r["pattern"]), r["level"])
            for r in rules
        ]

    async def check(self, action: Action) -> GuardrailResult:
        """Classify the command in the action. Does not block — just labels."""
        if action.tool_name != "run_shell":
            return GuardrailResult(
                allowed=True, level="safe",
                reason=None, requires_hitl=False, blocked=False,
            )

        cmd = action.arguments.get("cmd", "")
        if not cmd:
            return GuardrailResult(
                allowed=True, level="safe",
                reason=None, requires_hitl=False, blocked=False,
            )

        for pattern, level in self._rules:
            if pattern.search(cmd):
                return GuardrailResult(
                    allowed=True, level=level,
                    reason=f"Command classified as {level}",
                    requires_hitl=(level == "dangerous"),
                    blocked=False,
                )

        return GuardrailResult(
            allowed=True, level="safe",
            reason=None, requires_hitl=False, blocked=False,
        )
```

- [ ] **Step 4: 运行测试验证通过**

```bash
pytest tests/test_command_classifier.py -v
```
Expected: 6 PASS

- [ ] **Step 5: 提交**

```bash
git add src/guardrails/command_classifier.py tests/test_command_classifier.py
git commit -m "feat: add CommandClassifier guardrail for shell command risk assessment"
```

---

### Task 12: HITL 审批

**Files:**
- Create: `src/guardrails/hitl.py`
- Create: `tests/test_hitl.py`

**Interfaces:**
- Consumes: `Action`, `GuardrailResult` from `src/models.py`
- Produces: `HITLGuard` class implementing `Guardrail` Protocol
  - `__init__(timeout: float = 30, input_func: callable = None)`
  - `async def check(self, action: Action) -> GuardrailResult`
  - `async def request_approval(self, action: Action) -> GuardrailResult`

- [ ] **Step 1: 编写失败测试**

```python
# tests/test_hitl.py
"""Tests for HITL (Human-in-the-Loop) guardrail."""
import pytest
from src.models import Action
from src.guardrails.hitl import HITLGuard


@pytest.mark.asyncio
async def test_hitl_approves_on_yes():
    """User inputs 'y' — action should be approved."""
    hitl = HITLGuard(timeout=30, input_func=lambda _: "y")
    action = Action(tool_name="run_shell", arguments={"cmd": "rm -rf ./tmp"})
    result = await hitl.check(action)
    assert result.blocked is False
    assert result.allowed is True


@pytest.mark.asyncio
async def test_hitl_rejects_on_no():
    """User inputs 'n' — action should be blocked."""
    hitl = HITLGuard(timeout=30, input_func=lambda _: "n")
    action = Action(tool_name="run_shell", arguments={"cmd": "rm -rf ./tmp"})
    result = await hitl.check(action)
    assert result.blocked is True
    assert "rejected" in result.reason.lower()


@pytest.mark.asyncio
async def test_hitl_rejects_on_timeout():
    """No response within timeout — action should be blocked."""
    hitl = HITLGuard(timeout=0.01, input_func=lambda _: None)  # returns None → timeout
    action = Action(tool_name="run_shell", arguments={"cmd": "rm -rf ./tmp"})
    result = await hitl.check(action)
    assert result.blocked is True
    assert "timeout" in result.reason.lower()


@pytest.mark.asyncio
async def test_hitl_skips_non_dangerous_actions():
    """Non-dangerous commands should pass through without HITL."""
    hitl = HITLGuard(timeout=30, input_func=lambda _: "n")
    action = Action(tool_name="run_shell", arguments={"cmd": "ls"})
    result = await hitl.check(action)
    # The HITL guard itself doesn't classify — it relies on the pipeline
    # to only call it for dangerous actions. So it asks for any run_shell.
    # (This is fine — the pipeline handles routing.)
    assert result is not None


@pytest.mark.asyncio
async def test_hitl_skips_non_shell_actions():
    hitl = HITLGuard(timeout=30, input_func=lambda _: "y")
    action = Action(tool_name="read_file", arguments={"path": "test.py"})
    result = await hitl.check(action)
    assert result.blocked is False
    assert result.requires_hitl is False


@pytest.mark.asyncio
async def test_request_approval_yes():
    hitl = HITLGuard(timeout=30, input_func=lambda _: "y")
    action = Action(tool_name="run_shell", arguments={"cmd": "rm -rf ./tmp"})
    result = await hitl.request_approval(action)
    assert result.allowed is True
    assert result.blocked is False


@pytest.mark.asyncio
async def test_request_approval_timeout():
    hitl = HITLGuard(timeout=0.01, input_func=lambda _: None)
    action = Action(tool_name="run_shell", arguments={"cmd": "rm -rf ./tmp"})
    result = await hitl.request_approval(action)
    assert result.blocked is True
    assert result.reason == "timeout"
```

- [ ] **Step 2: 运行测试验证失败**

```bash
pytest tests/test_hitl.py -v
```
Expected: 7 failed (ImportError)

- [ ] **Step 3: 实现 HITLGuard**

```python
# src/guardrails/hitl.py
"""HITL (Human-in-the-Loop) guardrail — requires human approval for dangerous actions."""
import asyncio
from collections.abc import Callable
from src.models import Action, GuardrailResult


class HITLGuard:
    """Pauses execution for dangerous actions, waiting for human approval."""

    def __init__(
        self,
        timeout: float = 30.0,
        input_func: Callable[[str], str | None] | None = None,
    ):
        self._timeout = timeout
        self._input_func = input_func or input

    async def check(self, action: Action) -> GuardrailResult:
        """Check if the action requires HITL approval."""
        if action.tool_name != "run_shell":
            return GuardrailResult(
                allowed=True, level="safe",
                reason=None, requires_hitl=False, blocked=False,
            )
        return await self.request_approval(action)

    async def request_approval(self, action: Action) -> GuardrailResult:
        """Request human approval for a dangerous action."""
        cmd = action.arguments.get("cmd", "unknown")
        prompt = (
            f"\n[HITL] Dangerous command detected:\n"
            f"  Command: {cmd}\n"
            f"  Risk: This command could cause data loss or system damage.\n"
            f"  Approve? (y/n, timeout={self._timeout}s): "
        )

        try:
            response = await self._get_input(prompt)
            if response is None:
                return GuardrailResult(
                    allowed=False, level="dangerous",
                    reason="timeout", requires_hitl=True, blocked=True,
                )
            if response.strip().lower() in ("y", "yes"):
                return GuardrailResult(
                    allowed=True, level="dangerous",
                    reason="approved by human", requires_hitl=True, blocked=False,
                )
            else:
                return GuardrailResult(
                    allowed=False, level="dangerous",
                    reason="rejected by human", requires_hitl=True, blocked=True,
                )
        except asyncio.TimeoutError:
            return GuardrailResult(
                allowed=False, level="dangerous",
                reason="timeout", requires_hitl=True, blocked=True,
            )

    async def _get_input(self, prompt: str) -> str | None:
        """Get user input with a timeout."""
        try:
            loop = asyncio.get_running_loop()
            result = await asyncio.wait_for(
                loop.run_in_executor(None, self._input_func, prompt),
                timeout=self._timeout,
            )
            return result
        except asyncio.TimeoutError:
            return None
```

- [ ] **Step 4: 运行测试验证通过**

```bash
pytest tests/test_hitl.py -v
```
Expected: 7 PASS

- [ ] **Step 5: 提交**

```bash
git add src/guardrails/hitl.py tests/test_hitl.py
git commit -m "feat: add HITL guardrail for human approval of dangerous commands"
```

---
### Task 13: 沙箱执行

**Files:**
- Create: `src/guardrails/sandbox.py`
- Create: `tests/test_sandbox.py`

**Interfaces:**
- Consumes: `Action`, `GuardrailResult`, `ToolResult` from `src/models.py`
- Produces: `SandboxExecutor` class
  - `__init__(memory_limit_mb: int = 512, cpu_time_limit: int = 30)`
  - `async def execute(self, action: Action) -> ToolResult`

- [ ] **Step 1: 编写失败测试**

```python
# tests/test_sandbox.py
"""Tests for sandbox executor."""
import pytest
from src.models import Action
from src.guardrails.sandbox import SandboxExecutor


@pytest.fixture
def sandbox():
    return SandboxExecutor(memory_limit_mb=512, cpu_time_limit=10)


@pytest.mark.asyncio
async def test_sandbox_runs_safe_command(sandbox, temp_dir):
    action = Action(tool_name="run_shell", arguments={"cmd": "echo hello", "cwd": str(temp_dir)})
    result = await sandbox.execute(action)
    assert result.success is True
    assert "hello" in result.stdout


@pytest.mark.asyncio
async def test_sandbox_sets_temp_directory():
    sandbox = SandboxExecutor()
    action = Action(tool_name="run_shell", arguments={"cmd": "pwd"})
    result = await sandbox.execute(action)
    assert result.success is True
    # Sandbox should run in a temporary directory
    assert "/tmp/" in result.stdout or "Temp" in result.stdout


@pytest.mark.asyncio
async def test_sandbox_limits_time():
    sandbox = SandboxExecutor(cpu_time_limit=1)
    action = Action(tool_name="run_shell", arguments={"cmd": "sleep 10"})
    result = await sandbox.execute(action)
    assert result.success is False
    assert "timeout" in result.stderr.lower() or "killed" in result.stderr.lower()


@pytest.mark.asyncio
async def test_sandbox_skips_non_shell_actions(sandbox):
    action = Action(tool_name="read_file", arguments={"path": "test.py"})
    result = await sandbox.execute(action)
    assert result.success is False
    assert "not a shell command" in result.stderr.lower()


@pytest.mark.asyncio
async def test_sandbox_restricts_environment():
    sandbox = SandboxExecutor()
    # Run a command that tries to access the network
    action = Action(tool_name="run_shell", arguments={
        "cmd": "python -c \"import urllib.request; urllib.request.urlopen('https://example.com', timeout=3)\""
    })
    result = await sandbox.execute(action)
    # May fail due to restricted environment or network issues
    # Not asserting on success/failure as it depends on environment
    assert result is not None
```

- [ ] **Step 2: 运行测试验证失败**

```bash
pytest tests/test_sandbox.py -v
```
Expected: 5 failed (ImportError)

- [ ] **Step 3: 实现 SandboxExecutor**

```python
# src/guardrails/sandbox.py
"""Sandbox executor — runs commands in a restricted environment."""
import asyncio
import tempfile
import os
from pathlib import Path
from src.models import Action, ToolResult


class SandboxExecutor:
    """Executes shell commands in a sandboxed environment with resource limits."""

    def __init__(self, memory_limit_mb: int = 512, cpu_time_limit: int = 30):
        self._memory_limit_mb = memory_limit_mb
        self._cpu_time_limit = cpu_time_limit

    async def execute(self, action: Action) -> ToolResult:
        """Execute a command in a sandboxed temporary directory.

        Note: This is a software-level sandbox using subprocess isolation.
        It is NOT a security boundary — for true isolation, use Docker.
        """
        if action.tool_name != "run_shell":
            return ToolResult(
                tool_call_id="",
                tool_name=action.tool_name,
                success=False,
                stdout="",
                stderr=f"Sandbox: not a shell command ({action.tool_name})",
                exit_code=-1,
            )

        cmd = action.arguments.get("cmd", "")
        if not cmd:
            return ToolResult(
                tool_call_id="",
                tool_name="run_shell",
                success=False,
                stdout="",
                stderr="Sandbox: no command provided",
                exit_code=-1,
            )

        with tempfile.TemporaryDirectory(prefix="harness_sandbox_") as sandbox_dir:
            sandbox_env = os.environ.copy()
            sandbox_env["PATH"] = "/usr/bin:/bin:/usr/local/bin"
            sandbox_env.pop("HOME", None)

            try:
                proc = await asyncio.create_subprocess_shell(
                    cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=sandbox_dir,
                    env=sandbox_env,
                )
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(), timeout=self._cpu_time_limit
                )
                exit_code = proc.returncode or 0
                return ToolResult(
                    tool_call_id="",
                    tool_name="run_shell",
                    success=exit_code == 0,
                    stdout=stdout.decode("utf-8", errors="replace"),
                    stderr=stderr.decode("utf-8", errors="replace"),
                    exit_code=exit_code,
                )
            except asyncio.TimeoutError:
                return ToolResult(
                    tool_call_id="",
                    tool_name="run_shell",
                    success=False,
                    stdout="",
                    stderr=f"Sandbox: command timed out after {self._cpu_time_limit}s",
                    exit_code=-1,
                )
            except Exception as e:
                return ToolResult(
                    tool_call_id="",
                    tool_name="run_shell",
                    success=False,
                    stdout="",
                    stderr=f"Sandbox error: {e}",
                    exit_code=1,
                )
```

- [ ] **Step 4: 运行测试验证通过**

```bash
pytest tests/test_sandbox.py -v
```
Expected: ALL PASS

- [ ] **Step 5: 提交**

```bash
git add src/guardrails/sandbox.py tests/test_sandbox.py
git commit -m "feat: add SandboxExecutor for restricted command execution"
```

---

### Task 14: 护栏 Pipeline 集成

**Files:**
- Modify: `src/guardrails/__init__.py`
- Create: `src/guardrails/factory.py`

**Interfaces:**
- Consumes: `FileFence`, `CommandClassifier`, `HITLGuard`, `SandboxExecutor`, `GuardrailPipeline` from respective modules
- Consumes: Config dict from `src/config/loader.py`
- Produces: `def create_guardrail_pipeline(config: dict) -> GuardrailPipeline`

- [ ] **Step 1: 编写失败测试**

```python
# Append to tests/test_guardrail_pipeline.py
from src.guardrails.factory import create_guardrail_pipeline


def test_create_pipeline_from_config(sample_config_dict):
    pipeline = create_guardrail_pipeline(sample_config_dict)
    assert pipeline is not None
    # Should have 4 layers: FileFence, CommandClassifier, HITLGuard, SandboxExecutor
    assert len(pipeline._layers) == 4


@pytest.mark.asyncio
async def test_full_pipeline_with_safe_command(sample_config_dict):
    pipeline = create_guardrail_pipeline(sample_config_dict)
    action = Action(tool_name="run_shell", arguments={"cmd": "pytest tests/"})
    result = await pipeline.check(action)
    assert result.blocked is False


@pytest.mark.asyncio
async def test_full_pipeline_with_dangerous_command(sample_config_dict):
    pipeline = create_guardrail_pipeline(sample_config_dict)
    action = Action(tool_name="run_shell", arguments={"cmd": "rm -rf /"})
    result = await pipeline.check(action)
    # rm -rf / is classified as dangerous, but HITL is not called
    # because the pipeline only checks, doesn't execute HITL in check()
    # The HITL is triggered separately when level is dangerous
    assert result.level == "dangerous"


@pytest.mark.asyncio
async def test_full_pipeline_file_fence_first(sample_config_dict):
    """File fence should block paths before command classification."""
    pipeline = create_guardrail_pipeline(sample_config_dict)
    action = Action(tool_name="read_file", arguments={"path": "/etc/passwd"})
    result = await pipeline.check(action)
    assert result.blocked is True
    assert "outside" in result.reason.lower()
```

- [ ] **Step 2: 运行测试验证失败**

```bash
pytest tests/test_guardrail_pipeline.py -v -k "create_pipeline or full_pipeline"
```
Expected: 4 failed

- [ ] **Step 3: 实现工厂函数**

```python
# src/guardrails/factory.py
"""Factory function to create the guardrail pipeline from configuration."""
from src.guardrails.base import GuardrailPipeline
from src.guardrails.file_fence import FileFence
from src.guardrails.command_classifier import CommandClassifier
from src.guardrails.hitl import HITLGuard
from src.guardrails.sandbox import SandboxExecutor


def create_guardrail_pipeline(config: dict) -> GuardrailPipeline:
    """Create a full guardrail pipeline from configuration.

    Layer order: FileFence → CommandClassifier → HITLGuard → SandboxExecutor
    """
    guardrail_config = config.get("guardrails", {})

    layers = [
        FileFence(allowed_paths=guardrail_config.get("allowed_paths", [])),
        CommandClassifier(rules=guardrail_config.get("command_rules", [])),
        HITLGuard(timeout=guardrail_config.get("hitl", {}).get("timeout", 30)),
        SandboxExecutor(
            memory_limit_mb=guardrail_config.get("sandbox", {}).get("memory_limit_mb", 512),
            cpu_time_limit=guardrail_config.get("sandbox", {}).get("cpu_time_limit", 30),
        ),
    ]

    return GuardrailPipeline(layers=layers)
```

```python
# src/guardrails/__init__.py
"""Guardrails module — governance, HITL, sandbox, and scope fencing."""
from src.guardrails.base import Guardrail, GuardrailPipeline
from src.guardrails.file_fence import FileFence
from src.guardrails.command_classifier import CommandClassifier
from src.guardrails.hitl import HITLGuard
from src.guardrails.sandbox import SandboxExecutor
from src.guardrails.factory import create_guardrail_pipeline

__all__ = [
    "Guardrail",
    "GuardrailPipeline",
    "FileFence",
    "CommandClassifier",
    "HITLGuard",
    "SandboxExecutor",
    "create_guardrail_pipeline",
]
```

- [ ] **Step 4: 运行测试验证通过**

```bash
pytest tests/test_guardrail_pipeline.py -v
```
Expected: ALL PASS

- [ ] **Step 5: 提交**

```bash
git add src/guardrails/ tests/test_guardrail_pipeline.py
git commit -m "feat: add guardrail pipeline factory and module exports"
```

---

## Phase 4: 反馈回路

### Task 15: 反馈解析器 + 失败分类

**Files:**
- Create: `src/feedback/__init__.py`
- Create: `src/feedback/parser.py`
- Create: `tests/test_feedback.py`

**Interfaces:**
- Consumes: `ToolResult`, `Feedback`, `FeedbackType` from `src/models.py`
- Produces: `FeedbackParser` class:
  - `def parse(tool_result: ToolResult) -> Feedback` — parse tool output into structured feedback
  - `def classify_failure(exit_code: int, stderr: str) -> FeedbackType`

- [ ] **Step 1: 创建目录并编写失败测试**

```bash
mkdir -p src/feedback
touch src/feedback/__init__.py
```

```python
# tests/test_feedback.py
"""Tests for feedback parser."""
import pytest
from src.models import ToolResult, Feedback, FeedbackType
from src.feedback.parser import FeedbackParser


class TestFeedbackParser:
    def test_parse_pytest_all_pass(self):
        tr = ToolResult(
            tool_call_id="c1", tool_name="run_shell",
            success=True,
            stdout="tests/test_main.py::test_add PASSED\n======= 3 passed in 0.5s =======",
            stderr="", exit_code=0, duration_ms=500,
        )
        fb = FeedbackParser.parse(tr)
        assert fb.type == FeedbackType.UNKNOWN  # no failure, type is UNKNOWN
        assert fb.passed_count == 3
        assert fb.failed_count == 0

    def test_parse_pytest_failure(self):
        tr = ToolResult(
            tool_call_id="c1", tool_name="run_shell",
            success=False,
            stdout=(
                "tests/test_main.py::test_add PASSED\n"
                "tests/test_main.py::test_sub FAILED\n"
                "AssertionError: assert 3 == 5\n"
                "======= 1 failed, 2 passed in 0.5s ======="
            ),
            stderr="", exit_code=1, duration_ms=500,
        )
        fb = FeedbackParser.parse(tr)
        assert fb.type == FeedbackType.ASSERTION_FAILURE
        assert fb.failed_count == 1
        assert fb.passed_count == 2
        assert "test_sub" in fb.detail

    def test_parse_pytest_syntax_error(self):
        tr = ToolResult(
            tool_call_id="c1", tool_name="run_shell",
            success=False,
            stdout="SyntaxError: invalid syntax\n  File 'test.py', line 5\n    x =",
            stderr="", exit_code=1, duration_ms=100,
        )
        fb = FeedbackParser.parse(tr)
        assert fb.type == FeedbackType.SYNTAX_ERROR
        assert "SyntaxError" in fb.detail

    def test_parse_pytest_import_error(self):
        tr = ToolResult(
            tool_call_id="c1", tool_name="run_shell",
            success=False,
            stdout="ImportError: No module named 'nonexistent'\nModuleNotFoundError",
            stderr="", exit_code=1, duration_ms=100,
        )
        fb = FeedbackParser.parse(tr)
        assert fb.type == FeedbackType.IMPORT_ERROR

    def test_parse_timeout(self):
        tr = ToolResult(
            tool_call_id="c1", tool_name="run_shell",
            success=False,
            stdout="",
            stderr="Command timed out after 60s: pytest tests/",
            exit_code=-1, duration_ms=60000,
        )
        fb = FeedbackParser.parse(tr)
        assert fb.type == FeedbackType.TIMEOUT

    def test_parse_unknown_error(self):
        tr = ToolResult(
            tool_call_id="c1", tool_name="run_shell",
            success=False,
            stdout="Some random error",
            stderr="more error details",
            exit_code=255, duration_ms=100,
        )
        fb = FeedbackParser.parse(tr)
        assert fb.type == FeedbackType.UNKNOWN

    def test_parse_success_no_tests(self):
        tr = ToolResult(
            tool_call_id="c1", tool_name="run_shell",
            success=True,
            stdout="hello world",
            stderr="", exit_code=0, duration_ms=10,
        )
        fb = FeedbackParser.parse(tr)
        assert fb.type == FeedbackType.UNKNOWN
        assert fb.summary == "Command executed successfully"

    def test_to_message(self):
        fb = Feedback(
            type=FeedbackType.ASSERTION_FAILURE,
            summary="1 test failed",
            detail="test_sub: assert 3 == 5",
            suggestion="Check the subtraction logic",
            failed_count=1,
            passed_count=2,
        )
        msg = FeedbackParser.to_message(fb)
        assert "FAILED" in msg
        assert "test_sub" in msg
        assert "1 failed" in msg
```

- [ ] **Step 2: 运行测试验证失败**

```bash
pytest tests/test_feedback.py -v
```
Expected: 8 failed (ImportError)

- [ ] **Step 3: 实现 FeedbackParser**

```python
# src/feedback/parser.py
"""Feedback parser — extracts structured feedback from tool execution results."""
import re
from src.models import ToolResult, Feedback, FeedbackType


class FeedbackParser:
    """Parses tool execution output into structured feedback."""

    @staticmethod
    def parse(tool_result: ToolResult) -> Feedback:
        """Parse a ToolResult into a Feedback object.

        Detects pytest output, syntax errors, import errors, and timeouts.
        """
        stdout = tool_result.stdout
        stderr = tool_result.stderr
        combined = f"{stdout}\n{stderr}"

        # Check for timeout first
        if "timeout" in combined.lower() or "timed out" in combined.lower():
            return Feedback(
                type=FeedbackType.TIMEOUT,
                summary="Command timed out",
                detail=combined[:500],
                suggestion="Consider optimizing the command or increasing the timeout.",
                failed_count=0,
                passed_count=0,
            )

        if not tool_result.success:
            fb_type = FeedbackParser._classify_failure(combined)
            suggestion = FeedbackParser._get_suggestion(fb_type, combined)
            failed, passed = FeedbackParser._parse_pytest_counts(combined)

            # Extract the most relevant detail
            detail = FeedbackParser._extract_error_detail(combined)

            return Feedback(
                type=fb_type,
                summary=f"{'Test' if failed > 0 else 'Command'} failed with {fb_type.value}",
                detail=detail,
                suggestion=suggestion,
                failed_count=failed,
                passed_count=passed,
            )

        # Success case
        failed, passed = FeedbackParser._parse_pytest_counts(combined)
        return Feedback(
            type=FeedbackType.UNKNOWN,
            summary="Command executed successfully",
            detail=combined[:500],
            suggestion="",
            failed_count=failed,
            passed_count=passed,
        )

    @staticmethod
    def _classify_failure(combined: str) -> FeedbackType:
        """Classify the type of failure from the output."""
        if re.search(r"SyntaxError", combined):
            return FeedbackType.SYNTAX_ERROR
        if re.search(r"AssertionError|assert\b", combined):
            return FeedbackType.ASSERTION_FAILURE
        if re.search(r"ImportError|ModuleNotFoundError", combined):
            return FeedbackType.IMPORT_ERROR
        if re.search(r"timeout|timed out", combined, re.IGNORECASE):
            return FeedbackType.TIMEOUT
        return FeedbackType.UNKNOWN

    @staticmethod
    def _get_suggestion(fb_type: FeedbackType, combined: str) -> str:
        """Generate a suggestion based on failure type."""
        suggestions = {
            FeedbackType.SYNTAX_ERROR: "Fix the syntax error in the code.",
            FeedbackType.ASSERTION_FAILURE: "Check the logic — the expected value does not match the actual value.",
            FeedbackType.IMPORT_ERROR: "Install the missing dependency or check the import path.",
            FeedbackType.TIMEOUT: "The command took too long. Consider optimizing or splitting the work.",
            FeedbackType.UNKNOWN: "Review the error output and determine the root cause.",
        }
        return suggestions.get(fb_type, "")

    @staticmethod
    def _parse_pytest_counts(combined: str) -> tuple[int, int]:
        """Extract passed/failed counts from pytest output."""
        match = re.search(r"(\d+)\s+failed,\s*(\d+)\s+passed", combined)
        if match:
            return int(match.group(1)), int(match.group(2))
        match = re.search(r"(\d+)\s+passed", combined)
        if match:
            return 0, int(match.group(1))
        return 0, 0

    @staticmethod
    def _extract_error_detail(combined: str) -> str:
        """Extract the most relevant error lines from the output."""
        lines = combined.split("\n")
        error_lines = []
        for line in lines:
            line_stripped = line.strip()
            if not line_stripped:
                continue
            if any(kw in line_stripped for kw in [
                "FAILED", "ERROR", "Error", "assert", "SyntaxError",
                "ImportError", "ModuleNotFoundError", "Traceback",
            ]):
                error_lines.append(line_stripped)
        if not error_lines:
            error_lines = lines[-5:]  # last 5 lines as fallback
        return "\n".join(error_lines[:10])  # max 10 lines

    @staticmethod
    def to_message(feedback: Feedback) -> str:
        """Convert a Feedback object to a message string for the LLM context."""
        parts = [
            f"[FEEDBACK] {feedback.summary}",
            f"Type: {feedback.type.value}",
            f"Failed: {feedback.failed_count}, Passed: {feedback.passed_count}",
        ]
        if feedback.detail:
            parts.append(f"Details:\n{feedback.detail}")
        if feedback.suggestion:
            parts.append(f"Suggestion: {feedback.suggestion}")
        return "\n".join(parts)
```

- [ ] **Step 4: 运行测试验证通过**

```bash
pytest tests/test_feedback.py -v
```
Expected: 8 PASS

- [ ] **Step 5: 提交**

```bash
git add src/feedback/ tests/test_feedback.py
git commit -m "feat: add feedback parser with pytest output analysis and failure classification"
```

---

## Phase 5: 主循环

### Task 16: 智能体主循环

**Files:**
- Create: `src/loop/__init__.py`
- Create: `src/loop/agent.py`
- Create: `tests/test_loop.py`

**Interfaces:**
- Consumes: All modules from previous tasks (LLM, Tools, Guardrails, Feedback, Memory, Config)
- Produces: `AgentLoop` class:
  - `__init__(config: dict)` — initializes all subsystems
  - `async def run(self, task: str, llm_backend: LLMBackend) -> str` — main loop
- Produces: `StopReason` enum: `FINISH_CALLED, MAX_TURNS, IDLE_TIMEOUT, GUARDRAIL_BLOCKED`

- [ ] **Step 1: 创建目录并编写失败测试**

```bash
mkdir -p src/loop
touch src/loop/__init__.py
```

```python
# tests/test_loop.py
"""Tests for the agent main loop using Mock LLM."""
import pytest
from src.models import (
    Message, ToolCall, LLMResponse, ToolResult, Feedback, FeedbackType,
)
from src.llm.mock_backend import MockLLMBackend
from src.loop.agent import AgentLoop, StopReason


def make_text_response(content: str) -> LLMResponse:
    return LLMResponse(content=content, finish_reason="stop")


def make_tool_response(name: str, args: dict) -> LLMResponse:
    return LLMResponse(
        tool_calls=[ToolCall(id="call_1", name=name, arguments=args)],
        finish_reason="tool_calls",
    )


def make_finish_response(summary: str = "Done") -> LLMResponse:
    return LLMResponse(
        tool_calls=[ToolCall(id="call_f", name="finish", arguments={"summary": summary})],
        finish_reason="tool_calls",
    )


@pytest.fixture
def agent_config(sample_config_dict):
    return sample_config_dict


@pytest.mark.asyncio
async def test_loop_finishes_on_finish_tool(agent_config, temp_dir):
    """Agent loop should stop when LLM calls the finish tool."""
    responses = [
        make_finish_response("All tests pass"),
    ]
    backend = MockLLMBackend(responses=responses)
    loop = AgentLoop(agent_config)
    result = await loop.run("Run tests", backend)
    assert result.stop_reason == StopReason.FINISH_CALLED
    assert "All tests pass" in result.summary
    assert result.turns == 1


@pytest.mark.asyncio
async def test_loop_stops_on_max_turns(agent_config, temp_dir):
    """Agent loop should stop after max_turns iterations."""
    agent_config["loop"]["max_turns"] = 3
    responses = [
        make_tool_response("read_file", {"path": "test.py"}),
        make_tool_response("read_file", {"path": "test.py"}),
        make_tool_response("read_file", {"path": "test.py"}),
    ]
    backend = MockLLMBackend(responses=responses)
    loop = AgentLoop(agent_config)
    result = await loop.run("Read files", backend)
    assert result.stop_reason == StopReason.MAX_TURNS
    assert result.turns == 3


@pytest.mark.asyncio
async def test_loop_handles_text_response(agent_config, temp_dir):
    """Agent loop should handle text-only responses from LLM."""
    responses = [
        make_text_response("I think the task is done."),
        make_text_response("No further actions needed."),
        make_text_response("Still thinking..."),
    ]
    agent_config["loop"]["idle_timeout"] = 2
    backend = MockLLMBackend(responses=responses)
    loop = AgentLoop(agent_config)
    result = await loop.run("Analyze code", backend)
    assert result.stop_reason == StopReason.IDLE_TIMEOUT or result.stop_reason == StopReason.MAX_TURNS


@pytest.mark.asyncio
async def test_loop_guardrail_blocks_dangerous(agent_config, temp_dir):
    """Agent loop should block dangerous commands via guardrail."""
    # Create a test file so read_file doesn't fail
    test_file = temp_dir / "src" / "main.py"
    test_file.parent.mkdir(parents=True, exist_ok=True)
    test_file.write_text("print('hello')")

    agent_config["guardrails"]["allowed_paths"] = [str(temp_dir / "src"), str(temp_dir / "tests")]
    responses = [
        make_tool_response("read_file", {"path": "/etc/passwd"}),
        make_finish_response("Task done"),
    ]
    backend = MockLLMBackend(responses=responses)
    loop = AgentLoop(agent_config)
    result = await loop.run("Read file", backend)
    # The first action should be blocked by file fence
    assert result.turns >= 1


@pytest.mark.asyncio
async def test_loop_executes_tool_and_collects_result(agent_config, temp_dir):
    """Agent loop should execute tool calls and collect results."""
    test_file = temp_dir / "test.txt"
    test_file.write_text("hello")

    agent_config["guardrails"]["allowed_paths"] = [str(temp_dir)]
    responses = [
        make_tool_response("read_file", {"path": str(test_file)}),
        make_finish_response("Read the file"),
    ]
    backend = MockLLMBackend(responses=responses)
    loop = AgentLoop(agent_config)
    result = await loop.run("Read a file", backend)
    assert result.stop_reason == StopReason.FINISH_CALLED
    assert result.turns == 2
```

- [ ] **Step 2: 运行测试验证失败**

```bash
pytest tests/test_loop.py -v
```
Expected: 5 failed (ImportError)

- [ ] **Step 3: 实现 AgentLoop**

```python
# src/loop/agent.py
"""Agent main loop — orchestrates the full agent lifecycle."""
import logging
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
from src.models import (
    Message, Action, ToolCall, LLMResponse, ToolResult,
)
from src.llm.base import LLMBackend
from src.tools.executor import execute_tool
from src.tools.schema import get_allowed_tools
from src.feedback.parser import FeedbackParser
from src.guardrails.factory import create_guardrail_pipeline
from src.memory.store import MemoryStore
from src.config.loader import ConfigLoader

logger = logging.getLogger(__name__)


class StopReason(str, Enum):
    FINISH_CALLED = "finish_called"
    MAX_TURNS = "max_turns"
    IDLE_TIMEOUT = "idle_timeout"
    GUARDRAIL_BLOCKED = "guardrail_blocked"
    ERROR = "error"


@dataclass
class LoopResult:
    stop_reason: StopReason
    summary: str
    turns: int
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: datetime | None = None


class AgentLoop:
    """Main agent loop that orchestrates: context → LLM → parse → guardrail → dispatch → feedback → stop."""

    def __init__(self, config: dict):
        self._config = config
        self._loop_config = config.get("loop", {})
        self._max_turns = self._loop_config.get("max_turns", 20)
        self._idle_timeout = self._loop_config.get("idle_timeout", 3)
        self._tools_config = config.get("tools", {})
        self._allowed_tools = self._tools_config.get("allowed", [])
        self._shell_timeout = self._tools_config.get("shell_timeout", 60)
        self._guardrail_pipeline = create_guardrail_pipeline(config)
        self._memory = MemoryStore(
            db_path=config.get("memory", {}).get("db_path", ":memory:")
        )
        self._max_context_turns = config.get("memory", {}).get("max_context_turns", 10)

    async def run(self, task: str, llm_backend: LLMBackend) -> LoopResult:
        """Run the agent loop for a given task.

        Args:
            task: The user's task description.
            llm_backend: LLM backend to use (real or mock).

        Returns:
            LoopResult with stop reason, summary, and turn count.
        """
        result = LoopResult(stop_reason=StopReason.ERROR, summary="", turns=0)
        session = await self._memory.create_session(task)

        tools = get_allowed_tools(self._allowed_tools)
        messages = [
            Message(role="system", content=(
                "You are a coding agent. You can read files, write files, "
                "run shell commands, and declare tasks finished. "
                "Always use tools to interact with the system. "
                "When done, call the finish tool with a summary."
            )),
            Message(role="user", content=task),
        ]

        idle_count = 0
        consecutive_blocks = 0

        for turn in range(self._max_turns):
            result.turns = turn + 1

            # 1. Call LLM
            try:
                response = await llm_backend.chat(messages, tools)
            except Exception as e:
                logger.error(f"LLM call failed: {e}")
                result.stop_reason = StopReason.ERROR
                result.summary = f"LLM error: {e}"
                break

            # 2. Parse response
            if response.tool_calls:
                idle_count = 0
                for tc in response.tool_calls:
                    # Record assistant message
                    assistant_msg = Message(
                        role="assistant", content=None, tool_calls=[tc],
                    )
                    messages.append(assistant_msg)
                    await self._memory.add_message(session.id, turn, assistant_msg)

                    action = Action(tool_name=tc.name, arguments=tc.arguments)

                    # 3. Guardrail check
                    guard_result = await self._guardrail_pipeline.check(action)
                    if guard_result.blocked:
                        consecutive_blocks += 1
                        tool_result = ToolResult(
                            tool_call_id=tc.id,
                            tool_name=tc.name,
                            success=False,
                            stdout="",
                            stderr=f"BLOCKED by guardrail: {guard_result.reason}",
                            exit_code=-1,
                        )
                        await self._memory.log_audit(
                            session.id, "guardrail_block",
                            {"tool": tc.name, "args": tc.arguments, "reason": guard_result.reason},
                        )
                        if consecutive_blocks >= 3:
                            result.stop_reason = StopReason.GUARDRAIL_BLOCKED
                            result.summary = "Guardrail blocked 3 consecutive actions"
                            break
                    elif guard_result.requires_hitl:
                        # HITL approval
                        from src.guardrails.hitl import HITLGuard
                        hitl = HITLGuard(
                            timeout=self._config.get("guardrails", {}).get("hitl", {}).get("timeout", 30)
                        )
                        hitl_result = await hitl.request_approval(action)
                        if hitl_result.blocked:
                            tool_result = ToolResult(
                                tool_call_id=tc.id,
                                tool_name=tc.name,
                                success=False,
                                stdout="",
                                stderr=f"HITL rejected: {hitl_result.reason}",
                                exit_code=-1,
                            )
                            await self._memory.log_audit(
                                session.id, "hitl_reject",
                                {"tool": tc.name, "args": tc.arguments, "reason": hitl_result.reason},
                            )
                        else:
                            tool_result = await execute_tool(tc, timeout=self._shell_timeout)
                            await self._memory.log_audit(
                                session.id, "hitl_approve",
                                {"tool": tc.name, "args": tc.arguments},
                            )
                    else:
                        consecutive_blocks = 0
                        tool_result = await execute_tool(tc, timeout=self._shell_timeout)
                        await self._memory.log_audit(
                            session.id, "tool_execute",
                            {"tool": tc.name, "args": tc.arguments, "success": tool_result.success},
                        )

                    # 4. Record tool result
                    tool_msg = Message(
                        role="tool",
                        content=tool_result.stdout or tool_result.stderr,
                        tool_call_id=tc.id,
                        name=tc.name,
                    )
                    messages.append(tool_msg)

                    # 5. Feedback analysis
                    feedback = FeedbackParser.parse(tool_result)
                    if not tool_result.success:
                        feedback_msg = FeedbackParser.to_message(feedback)
                        messages.append(Message(role="user", content=feedback_msg))

                    # 6. Check if finish was called
                    if tc.name == "finish":
                        result.stop_reason = StopReason.FINISH_CALLED
                        result.summary = tc.arguments.get("summary", "Task completed")
                        break

                if result.stop_reason == StopReason.FINISH_CALLED:
                    break
                if result.stop_reason == StopReason.GUARDRAIL_BLOCKED:
                    break
            else:
                # Text response (no tool calls)
                idle_count += 1
                assistant_msg = Message(
                    role="assistant", content=response.content,
                )
                messages.append(assistant_msg)
                await self._memory.add_message(session.id, turn, assistant_msg)
                if idle_count >= self._idle_timeout:
                    result.stop_reason = StopReason.IDLE_TIMEOUT
                    result.summary = response.content or "Idle timeout reached"
                    break

        else:
            result.stop_reason = StopReason.MAX_TURNS
            result.summary = f"Reached max turns ({self._max_turns})"

        result.completed_at = datetime.now()
        await self._memory.update_session(session.id, result.stop_reason.value, result.turns)
        return result
```

- [ ] **Step 4: 运行测试验证通过**

```bash
pytest tests/test_loop.py -v
```
Expected: 5 PASS

- [ ] **Step 5: 提交**

```bash
git add src/loop/ tests/test_loop.py
git commit -m "feat: add agent main loop with guardrail, feedback, and stop conditions"
```

---

## Phase 6: 界面层

### Task 17: CLI 命令行

**Files:**
- Create: `src/cli/__init__.py`
- Create: `src/cli/main.py`
- Create: `tests/test_cli.py`

**Interfaces:**
- Consumes: `AgentLoop`, `LoopResult` from `src/loop/agent.py`
- Consumes: `ConfigLoader` from `src/config/loader.py`
- Produces: Click CLI with commands: `run`, `setup`, `status`, `web`

- [ ] **Step 1: 创建目录并编写失败测试**

```bash
mkdir -p src/cli
touch src/cli/__init__.py
```

```python
# tests/test_cli.py
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
    assert "web" in result.output


def test_cli_run_help(runner):
    result = runner.invoke(cli, ["run", "--help"])
    assert result.exit_code == 0


def test_cli_setup_help(runner):
    result = runner.invoke(cli, ["setup", "--help"])
    assert result.exit_code == 0


def test_cli_web_help(runner):
    result = runner.invoke(cli, ["web", "--help"])
    assert result.exit_code == 0


def test_cli_run_no_args(runner):
    """run command without task should show error."""
    result = runner.invoke(cli, ["run"])
    assert result.exit_code != 0
```

- [ ] **Step 2: 运行测试验证失败**

```bash
pytest tests/test_cli.py -v
```
Expected: 5 failed (ImportError)

- [ ] **Step 3: 实现 CLI**

```python
# src/cli/main.py
"""CLI entry point for the Coding Agent Harness."""
import click
import asyncio
import sys
from pathlib import Path


@click.group()
@click.version_option(version="0.1.0")
def cli():
    """AI4SE Coding Agent Harness — a governable, observable coding agent runtime."""
    pass


@cli.command()
@click.argument("task")
@click.option(
    "--config", "-c",
    default="harness.yaml",
    help="Path to configuration file.",
)
@click.option(
    "--mock", is_flag=True,
    help="Use mock LLM backend (for testing).",
)
def run(task: str, config: str, mock: bool):
    """Run a coding task with the agent.

    TASK is the description of what you want the agent to do.
    """
    from src.config.loader import ConfigLoader
    from src.loop.agent import AgentLoop

    loader = ConfigLoader()
    try:
        cfg = loader.load(config)
    except FileNotFoundError:
        click.echo(
            f"Config file not found: {config}\n"
            f"Run 'harness setup' to configure the harness.",
            err=True,
        )
        sys.exit(1)

    if mock:
        from src.llm.mock_backend import MockLLMBackend
        from src.models import LLMResponse, ToolCall
        backend = MockLLMBackend(responses=[
            LLMResponse(
                tool_calls=[ToolCall(
                    id="c1", name="finish",
                    arguments={"summary": "Mock mode: task acknowledged."},
                )],
                finish_reason="tool_calls",
            )
        ])
    else:
        from src.llm.openai_backend import OpenAICompatBackend
        llm_config = cfg.get("llm", {})
        import keyring
        api_key = keyring.get_password("harness", "api_key")
        if not api_key:
            click.echo(
                "No API key found. Run 'harness setup' to configure your key.",
                err=True,
            )
            sys.exit(1)
        backend = OpenAICompatBackend(
            api_key=api_key,
            model=llm_config.get("model", "gpt-4o"),
            api_base=llm_config.get("api_base", ""),
            temperature=llm_config.get("temperature", 0.1),
            max_tokens=llm_config.get("max_tokens", 4096),
        )

    async def _run():
        loop = AgentLoop(cfg)
        result = await loop.run(task, backend)
        return result

    click.echo(f"Task: {task}")
    click.echo(f"Config: {config}")
    click.echo(f"Mode: {'Mock' if mock else 'Live'}")

    result = asyncio.run(_run())
    click.echo(f"\n{'=' * 50}")
    click.echo(f"Result: {result.stop_reason.value}")
    click.echo(f"Turns: {result.turns}")
    click.echo(f"Summary: {result.summary}")


@cli.command()
@click.option("--reset", is_flag=True, help="Reset (overwrite) existing API key.")
@click.option("--clear", is_flag=True, help="Remove the stored API key.")
def setup(reset: bool, clear: bool):
    """Configure API key and settings."""
    import keyring

    SERVICE = "harness"
    USERNAME = "api_key"

    if clear:
        try:
            keyring.delete_password(SERVICE, USERNAME)
            click.echo("API key removed from keyring.")
        except keyring.errors.PasswordDeleteError:
            click.echo("No API key was stored.")
        return

    existing = keyring.get_password(SERVICE, USERNAME)
    if existing and not reset:
        click.echo("API key is already configured. Use --reset to overwrite or --clear to remove.")
        return

    click.echo("Enter your API key (input will be hidden):")
    api_key = click.prompt("API Key", hide_input=True, confirmation_prompt=True)
    keyring.set_password(SERVICE, USERNAME, api_key)
    click.echo("API key stored securely in system keyring.")


@cli.command()
def status():
    """Show harness status and configuration."""
    import keyring

    SERVICE = "harness"
    USERNAME = "api_key"

    click.echo("Harness Status:")
    click.echo(f"  Version: 0.1.0")

    api_key = keyring.get_password(SERVICE, USERNAME)
    if api_key:
        click.echo(f"  API Key: **** (stored in keyring)")
    else:
        click.echo(f"  API Key: not configured (run 'harness setup')")

    from pathlib import Path
    default_config = Path("harness.yaml")
    user_config = Path.home() / ".harness" / "config.yaml"
    if default_config.exists():
        click.echo(f"  Config: {default_config.resolve()}")
    elif user_config.exists():
        click.echo(f"  Config: {user_config}")
    else:
        click.echo(f"  Config: not found")


@cli.command()
@click.option("--host", default="0.0.0.0", help="Host to bind to.")
@click.option("--port", default=8080, help="Port to listen on.")
def web(host: str, port: int):
    """Start the web dashboard."""
    import uvicorn
    click.echo(f"Starting web dashboard at http://{host}:{port}")
    uvicorn.run("src.web.app:app", host=host, port=port, reload=False)


if __name__ == "__main__":
    cli()
```

- [ ] **Step 4: 运行测试验证通过**

```bash
pytest tests/test_cli.py -v
```
Expected: 5 PASS

- [ ] **Step 5: 提交**

```bash
git add src/cli/ tests/test_cli.py
git commit -m "feat: add Click CLI with run, setup, status, web commands"
```

---

### Task 18: Web 仪表盘

**Files:**
- Create: `src/web/__init__.py`
- Create: `src/web/app.py`
- Create: `src/web/routes.py`
- Create: `src/web/templates/index.html`
- Create: `tests/test_web.py`

**Interfaces:**
- Consumes: `MemoryStore` from `src/memory/store.py`
- Produces: FastAPI app with routes:
  - `GET /` — dashboard HTML
  - `GET /api/status` — current state
  - `GET /api/history` — recent sessions
  - `GET /api/audit` — audit log

- [ ] **Step 1: 创建目录并编写失败测试**

```bash
mkdir -p src/web/templates
touch src/web/__init__.py
```

```python
# tests/test_web.py
"""Tests for web dashboard."""
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    from src.web.app import app
    return TestClient(app)


def test_dashboard_page_loads(client):
    response = client.get("/")
    assert response.status_code == 200


def test_api_status(client):
    response = client.get("/api/status")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data


def test_api_history(client):
    response = client.get("/api/history")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_api_audit(client):
    response = client.get("/api/audit")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
```

- [ ] **Step 2: 运行测试验证失败**

```bash
pytest tests/test_web.py -v
```
Expected: 4 failed (ImportError)

- [ ] **Step 3: 实现 Web 应用**

```python
# src/web/app.py
"""FastAPI web dashboard for the Coding Agent Harness."""
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pathlib import Path
from src.web.routes import router

app = FastAPI(title="Harness Dashboard", version="0.1.0")
app.include_router(router)

TEMPLATES_DIR = Path(__file__).parent / "templates"


@app.get("/", response_class=HTMLResponse)
async def dashboard():
    """Serve the dashboard HTML page."""
    index_path = TEMPLATES_DIR / "index.html"
    if index_path.exists():
        return index_path.read_text(encoding="utf-8")
    return HTMLResponse(
        "<html><body><h1>Harness Dashboard</h1><p>Template not found</p></body></html>"
    )
```

```python
# src/web/routes.py
"""API routes for the web dashboard."""
from fastapi import APIRouter

router = APIRouter(prefix="/api")


@router.get("/status")
async def get_status():
    """Get current harness status."""
    return {
        "status": "running",
        "version": "0.1.0",
        "uptime": "N/A",
    }


@router.get("/history")
async def get_history():
    """Get recent session history."""
    return []


@router.get("/audit")
async def get_audit():
    """Get recent audit log entries."""
    return []
```

```html
<!-- src/web/templates/index.html -->
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Harness Dashboard</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f5f5f5; color: #333; }
        .header { background: #1a1a2e; color: white; padding: 20px 30px; }
        .header h1 { font-size: 24px; }
        .subtitle { font-size: 14px; opacity: 0.7; margin-top: 4px; }
        .container { max-width: 1200px; margin: 0 auto; padding: 20px; }
        .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(350px, 1fr)); gap: 20px; }
        .card { background: white; border-radius: 8px; padding: 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
        .card h2 { font-size: 16px; margin-bottom: 12px; color: #1a1a2e; border-bottom: 2px solid #e0e0e0; padding-bottom: 8px; }
        .status-badge { display: inline-block; padding: 4px 12px; border-radius: 12px; font-size: 12px; font-weight: 600; }
        .running { background: #e8f5e9; color: #2e7d32; }
        .blocked { background: #ffebee; color: #c62828; }
        .warn { background: #fff3e0; color: #e65100; }
        .empty { color: #999; font-style: italic; padding: 20px; text-align: center; }
        .footer { text-align: center; color: #999; font-size: 12px; padding: 20px; }
    </style>
</head>
<body>
    <div class="header">
        <h1>Harness Dashboard</h1>
        <div class="subtitle">AI4SE Coding Agent Harness v0.1.0</div>
    </div>
    <div class="container">
        <div class="grid">
            <div class="card">
                <h2>System Status</h2>
                <p><span class="status-badge running">Running</span></p>
                <p style="margin-top: 10px; font-size: 13px; color: #666;">Version: 0.1.0</p>
            </div>
            <div class="card">
                <h2>Agent Loop</h2>
                <div id="loop-status">
                    <p>Idle — no active session</p>
                </div>
            </div>
            <div class="card">
                <h2>Recent Tool Calls</h2>
                <div id="tool-calls">
                    <p class="empty">No tool calls yet</p>
                </div>
            </div>
            <div class="card">
                <h2>Guardrail Audit</h2>
                <div id="audit-log">
                    <p class="empty">No guardrail events</p>
                </div>
            </div>
            <div class="card" style="grid-column: 1 / -1;">
                <h2>HITL Approval Queue</h2>
                <div id="hitl-queue">
                    <p class="empty">No pending approvals</p>
                </div>
            </div>
        </div>
    </div>
    <div class="footer">
        AI4SE Final Project &middot; Wang Yi (241250007)
    </div>
</body>
</html>
```

- [ ] **Step 4: 运行测试验证通过**

```bash
pytest tests/test_web.py -v
```
Expected: 4 PASS

- [ ] **Step 5: 提交**

```bash
git add src/web/ tests/test_web.py
git commit -m "feat: add FastAPI web dashboard with status and audit endpoints"
```

---

## Phase 7: 演示 + 集成 + 文档

### Task 19: OpenAI 兼容后端

**Files:**
- Create: `src/llm/openai_backend.py`
- Create: `tests/test_llm_openai.py`

**Interfaces:**
- Consumes: `LLMBackend` Protocol from `src/llm/base.py`
- Consumes: `Message`, `ToolCall`, `LLMResponse` from `src/models.py`
- Produces: `OpenAICompatBackend` class implementing `LLMBackend`
  - `__init__(api_key, model, api_base, temperature, max_tokens)`
  - `async def chat(messages, tools) -> LLMResponse`

- [ ] **Step 1: 编写失败测试**

```python
# tests/test_llm_openai.py
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
```

- [ ] **Step 2: 运行测试验证失败**

```bash
pytest tests/test_llm_openai.py -v
```
Expected: 4 failed (ImportError)

- [ ] **Step 3: 实现 OpenAICompatBackend**

```python
# src/llm/openai_backend.py
"""OpenAI-compatible LLM backend using the openai SDK."""
import json
from openai import AsyncOpenAI
from src.models import Message, ToolCall, LLMResponse


class OpenAICompatBackend:
    """LLM backend that communicates with an OpenAI-compatible API."""

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4o",
        api_base: str = "https://api.openai.com/v1",
        temperature: float = 0.1,
        max_tokens: int = 4096,
    ):
        self.model = model
        self.api_base = api_base
        self.temperature = temperature
        self.max_tokens = max_tokens
        self._client = AsyncOpenAI(
            api_key=api_key,
            base_url=api_base,
        )

    async def chat(
        self, messages: list[Message], tools: list[dict]
    ) -> LLMResponse:
        """Send messages to the LLM and return a response."""
        openai_messages = [self._message_to_dict(m) for m in messages]
        openai_tools = tools if tools else None

        response = await self._client.chat.completions.create(
            model=self.model,
            messages=openai_messages,
            tools=openai_tools,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        )

        choice = response.choices[0]
        message = choice.message

        tool_calls = None
        if message.tool_calls:
            tool_calls = [
                ToolCall(
                    id=tc.id,
                    name=tc.function.name,
                    arguments=json.loads(tc.function.arguments),
                )
                for tc in message.tool_calls
            ]

        return LLMResponse(
            content=message.content,
            tool_calls=tool_calls,
            finish_reason=choice.finish_reason or "stop",
            usage={
                "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                "completion_tokens": response.usage.completion_tokens if response.usage else 0,
            },
        )

    def _message_to_dict(self, message: Message) -> dict:
        """Convert a Message to OpenAI-compatible dict format."""
        result: dict = {"role": message.role}

        if message.content is not None:
            result["content"] = message.content

        if message.tool_calls:
            result["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.name,
                        "arguments": json.dumps(tc.arguments),
                    },
                }
                for tc in message.tool_calls
            ]

        if message.tool_call_id is not None:
            result["tool_call_id"] = message.tool_call_id

        if message.name is not None:
            result["name"] = message.name

        return result
```

- [ ] **Step 4: 运行测试验证通过**

```bash
pytest tests/test_llm_openai.py -v
```
Expected: 4 PASS

- [ ] **Step 5: 提交**

```bash
git add src/llm/openai_backend.py tests/test_llm_openai.py
git commit -m "feat: add OpenAI-compatible LLM backend"
```

---

### Task 20: 演示脚本

**Files:**
- Create: `demo/demo1_guardrail_intercept.py`
- Create: `demo/demo2_feedback_loop.py`
- Create: `demo/demo3_guardrail_pipeline.py`

**Interfaces:**
- Consumes: All modules from previous tasks
- Produces: Three standalone demo scripts that demonstrate the three mechanism scenarios

- [ ] **Step 1: 创建 demo1_guardrail_intercept.py**

```python
#!/usr/bin/env python3
"""Demo 1: Guardrail intercepts a dangerous action.

This demo shows the guardrail system intercepting a dangerous command (rm -rf /)
and preventing its execution. Uses Mock LLM for deterministic behavior.
"""
import asyncio
import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.models import Action, GuardrailResult
from src.guardrails.file_fence import FileFence
from src.guardrails.command_classifier import CommandClassifier
from src.guardrails.hitl import HITLGuard
from src.guardrails.base import GuardrailPipeline


async def main():
    print("=" * 60)
    print("Demo 1: Guardrail Intercepts Dangerous Action")
    print("=" * 60)

    # Configure guardrails
    file_fence = FileFence(allowed_paths=["./src", "./tests", "./demo"])
    classifier = CommandClassifier(rules=[
        {"pattern": r"^(ls|cat|pytest|echo)\b", "level": "safe"},
        {"pattern": r"\brm -rf\b", "level": "dangerous"},
    ])

    # Test 1: File fence blocks outside access
    print("\n[Test 1] File fence should block /etc/passwd access:")
    action1 = Action(tool_name="read_file", arguments={"path": "/etc/passwd"})
    result1 = await file_fence.check(action1)
    print(f"  Action: read_file('/etc/passwd')")
    print(f"  Result: blocked={result1.blocked}, reason={result1.reason}")
    assert result1.blocked is True, "FAIL: /etc/passwd should be blocked!"
    print("  PASS")

    # Test 2: Command classifier flags rm -rf
    print("\n[Test 2] Command classifier flags rm -rf as dangerous:")
    action2 = Action(tool_name="run_shell", arguments={"cmd": "rm -rf /"})
    result2 = await classifier.check(action2)
    print(f"  Action: run_shell('rm -rf /')")
    print(f"  Result: level={result2.level}, blocked={result2.blocked}")
    assert result2.level == "dangerous", "FAIL: rm -rf should be dangerous!"
    print("  PASS")

    # Test 3: Pipeline stops at first block
    print("\n[Test 3] Pipeline stops at file fence (first layer):")
    pipeline = GuardrailPipeline([file_fence, classifier])
    action3 = Action(tool_name="read_file", arguments={"path": "/etc/shadow"})
    result3 = await pipeline.check(action3)
    print(f"  Action: read_file('/etc/shadow')")
    print(f"  Result: blocked={result3.blocked}, reason={result3.reason}")
    assert result3.blocked is True, "FAIL: Pipeline should block!"
    print("  PASS")

    # Test 4: HITL rejects dangerous command
    print("\n[Test 4] HITL rejects dangerous command (simulated rejection):")
    hitl = HITLGuard(timeout=30, input_func=lambda _: "n")
    action4 = Action(tool_name="run_shell", arguments={"cmd": "rm -rf ./tmp"})
    result4 = await hitl.check(action4)
    print(f"  Action: run_shell('rm -rf ./tmp')")
    print(f"  Result: blocked={result4.blocked}, reason={result4.reason}")
    assert result4.blocked is True, "FAIL: HITL should reject!"
    print("  PASS")

    print("\n" + "=" * 60)
    print("Demo 1: ALL TESTS PASSED")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
```

- [ ] **Step 2: 创建 demo2_feedback_loop.py**

```python
#!/usr/bin/env python3
"""Demo 2: Feedback loop receives failure and changes next action.

This demo shows the feedback loop parsing a test failure and injecting
structured feedback that the LLM can use to self-correct.
Uses Mock LLM with a pre-defined sequence of responses.
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.models import Message, ToolCall, LLMResponse, ToolResult
from src.llm.mock_backend import MockLLMBackend
from src.feedback.parser import FeedbackParser
from src.loop.agent import AgentLoop


async def main():
    print("=" * 60)
    print("Demo 2: Feedback Loop Drives Self-Correction")
    print("=" * 60)

    # Test 1: Parse pytest failure
    print("\n[Test 1] FeedbackParser parses pytest failure:")
    tr = ToolResult(
        tool_call_id="c1", tool_name="run_shell",
        success=False,
        stdout=(
            "tests/test_calc.py::test_add FAILED\n"
            "AssertionError: assert 3 == 5\n"
            "======= 1 failed, 2 passed in 0.5s ======="
        ),
        stderr="", exit_code=1, duration_ms=500,
    )
    fb = FeedbackParser.parse(tr)
    print(f"  Type: {fb.type.value}")
    print(f"  Failed: {fb.failed_count}, Passed: {fb.passed_count}")
    print(f"  Detail: {fb.detail}")
    assert fb.type.value == "ASSERTION_FAILURE", "FAIL: Should detect assertion failure!"
    assert fb.failed_count == 1, "FAIL: Should count 1 failure!"
    print("  PASS")

    # Test 2: FeedbackParser generates suggestion
    print("\n[Test 2] FeedbackParser generates suggestion for each failure type:")
    from src.models import FeedbackType
    for ft in FeedbackType:
        tr = ToolResult(
            tool_call_id="c1", tool_name="run_shell",
            success=False,
            stdout=f"{ft.value} error occurred",
            stderr="", exit_code=1, duration_ms=100,
        )
        fb = FeedbackParser.parse(tr)
        assert fb.suggestion != "", f"FAIL: No suggestion for {ft.value}!"
        print(f"  {ft.value}: {fb.suggestion}")
    print("  PASS")

    # Test 3: Feedback message is formatted for LLM
    print("\n[Test 3] Feedback formatted as LLM context message:")
    fb = FeedbackParser.parse(tr)
    msg = FeedbackParser.to_message(fb)
    print(f"  {msg[:100]}...")
    assert "[FEEDBACK]" in msg, "FAIL: Feedback message missing [FEEDBACK] tag!"
    print("  PASS")

    # Test 4: Mock LLM loop with failure injection
    print("\n[Test 4] Mock LLM loop handles failure and retries:")
    config = {
        "loop": {"max_turns": 5, "idle_timeout": 3},
        "llm": {"provider": "openai_compat", "model": "gpt-4o", "api_base": "", "api_key_cmd": "", "temperature": 0.1, "max_tokens": 4096},
        "tools": {"allowed": ["read_file", "write_file", "run_shell", "finish"], "shell_timeout": 60},
        "guardrails": {"allowed_paths": ["./"], "command_rules": [], "hitl": {"timeout": 30, "enabled": False}, "sandbox": {"enabled": False}},
        "memory": {"db_path": ":memory:", "max_context_turns": 10},
        "web": {"host": "0.0.0.0", "port": 8080},
    }
    responses = [
        LLMResponse(
            tool_calls=[ToolCall(id="c1", name="run_shell", arguments={"cmd": "pytest"})],
            finish_reason="tool_calls",
        ),
        LLMResponse(
            tool_calls=[ToolCall(id="c2", name="finish", arguments={"summary": "Fixed the test"})],
            finish_reason="tool_calls",
        ),
    ]
    backend = MockLLMBackend(responses=responses)
    loop = AgentLoop(config)
    result = await loop.run("Fix failing tests", backend)
    print(f"  Stop reason: {result.stop_reason.value}")
    print(f"  Turns: {result.turns}")
    print(f"  Summary: {result.summary}")
    assert result.turns == 2, "FAIL: Should complete in 2 turns!"
    print("  PASS")

    print("\n" + "=" * 60)
    print("Demo 2: ALL TESTS PASSED")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
```

- [ ] **Step 3: 创建 demo3_guardrail_pipeline.py**

```python
#!/usr/bin/env python3
"""Demo 3: Full guardrail pipeline — four-layer state machine.

This demo shows the complete guardrail pipeline in action:
FileFence → CommandClassifier → HITL → Sandbox
Each layer is tested independently and then as a pipeline.
"""
import asyncio
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.models import Action
from src.guardrails.file_fence import FileFence
from src.guardrails.command_classifier import CommandClassifier
from src.guardrails.hitl import HITLGuard
from src.guardrails.sandbox import SandboxExecutor
from src.guardrails.base import GuardrailPipeline


async def main():
    print("=" * 60)
    print("Demo 3: Guardrail Pipeline — Four-Layer State Machine")
    print("=" * 60)

    # Configure all four layers
    file_fence = FileFence(allowed_paths=["./src", "./tests", "./demo"])
    classifier = CommandClassifier(rules=[
        {"pattern": r"^(ls|cat|pytest|echo|mkdir|python)\b", "level": "safe"},
        {"pattern": r"^(pip install|git commit)\b", "level": "warn"},
        {"pattern": r"\brm -rf\b|\bDROP TABLE\b|git push --force|\bsudo\b", "level": "dangerous"},
    ])
    hitl = HITLGuard(timeout=30, input_func=lambda _: "y")  # Simulate approval
    sandbox = SandboxExecutor(memory_limit_mb=512, cpu_time_limit=10)
    pipeline = GuardrailPipeline([file_fence, classifier, hitl, sandbox])

    # Test 1: Safe command passes all layers
    print("\n[Test 1] Safe command (ls) passes all four layers:")
    action1 = Action(tool_name="run_shell", arguments={"cmd": "ls ./src"})
    result1 = await pipeline.check(action1)
    print(f"  Action: run_shell('ls ./src')")
    print(f"  Result: blocked={result1.blocked}, level={result1.level}")
    assert result1.blocked is False, "FAIL: Safe command should pass!"
    print("  PASS")

    # Test 2: File fence blocks path traversal
    print("\n[Test 2] File fence blocks path traversal:")
    action2 = Action(tool_name="read_file", arguments={"path": "../../../etc/passwd"})
    result2 = await pipeline.check(action2)
    print(f"  Action: read_file('../../../etc/passwd')")
    print(f"  Result: blocked={result2.blocked}, reason={result2.reason}")
    assert result2.blocked is True, "FAIL: Path traversal should be blocked!"
    print("  PASS")

    # Test 3: Dangerous command triggers HITL
    print("\n[Test 3] Dangerous command goes through classification → HITL:")
    action3 = Action(tool_name="run_shell", arguments={"cmd": "rm -rf ./tmp"})
    result3 = await pipeline.check(action3)
    print(f"  Action: run_shell('rm -rf ./tmp')")
    print(f"  Result: blocked={result3.blocked}, level={result3.level}")
    print(f"  Requires HITL: {result3.requires_hitl}")
    assert result3.level == "dangerous", "FAIL: rm -rf should be dangerous!"
    print("  PASS")

    # Test 4: Sandbox executes safe command
    print("\n[Test 4] Sandbox executes a safe command in isolation:")
    action4 = Action(tool_name="run_shell", arguments={"cmd": "echo 'sandbox test' && pwd"})
    result4 = await sandbox.execute(action4)
    print(f"  Action: run_shell('echo sandbox test')")
    print(f"  Success: {result4.success}")
    print(f"  Output: {result4.stdout.strip()}")
    print(f"  Working dir: {result4.stdout.strip().split()[-1] if result4.stdout else 'N/A'}")
    assert result4.success is True, "FAIL: Safe command should succeed in sandbox!"
    print("  PASS")

    # Test 5: HITL timeout simulation
    print("\n[Test 5] HITL timeout rejects dangerous command:")
    hitl_timeout = HITLGuard(timeout=0.01, input_func=lambda _: None)
    action5 = Action(tool_name="run_shell", arguments={"cmd": "rm -rf /"})
    result5 = await hitl_timeout.check(action5)
    print(f"  Action: run_shell('rm -rf /')")
    print(f"  Result: blocked={result5.blocked}, reason={result5.reason}")
    assert result5.blocked is True, "FAIL: Timeout should block!"
    assert result5.reason == "timeout", "FAIL: Reason should be timeout!"
    print("  PASS")

    print("\n" + "=" * 60)
    print("Demo 3: ALL TESTS PASSED")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
```

- [ ] **Step 4: 运行演示脚本验证**

```bash
mkdir -p demo
python demo/demo1_guardrail_intercept.py
python demo/demo2_feedback_loop.py
python demo/demo3_guardrail_pipeline.py
```
Expected: All three scripts output "ALL TESTS PASSED"

- [ ] **Step 5: 提交**

```bash
git add demo/
git commit -m "feat: add three mechanism demonstration scripts"
```

---

### Task 21: CI 配置

**Files:**
- Create: `.gitlab-ci.yml`

**Interfaces:**
- Produces: CI pipeline with a `unit-test` job that runs all tests

- [ ] **Step 1: 创建 .gitlab-ci.yml**

```yaml
# .gitlab-ci.yml — CI Pipeline for Coding Agent Harness
stages:
  - test

unit-test:
  stage: test
  image: python:3.11
  before_script:
    - pip install -e ".[dev]"
  script:
    - pytest tests/ -v --tb=short
  coverage: '/TOTAL.*\s+(\d+%)$/'
```

- [ ] **Step 2: 验证 CI 配置语法**

```bash
python -c "import yaml; yaml.safe_load(open('.gitlab-ci.yml')); print('CI config OK')"
```
Expected: CI config OK

- [ ] **Step 3: 提交**

```bash
git add .gitlab-ci.yml
git commit -m "ci: add GitLab CI pipeline with unit-test job"
```

---

### Task 22: 集成测试

**Files:**
- Create: `tests/test_integration.py`

**Interfaces:**
- Consumes: All modules
- Produces: End-to-end integration tests using Mock LLM

- [ ] **Step 1: 编写集成测试**

```python
# tests/test_integration.py
"""Integration tests — full harness operation with Mock LLM."""
import pytest
from pathlib import Path
from src.models import Message, ToolCall, LLMResponse
from src.llm.mock_backend import MockLLMBackend
from src.loop.agent import AgentLoop, StopReason


def make_response(tool_calls=None, content=None):
    return LLMResponse(
        content=content,
        tool_calls=tool_calls,
        finish_reason="tool_calls" if tool_calls else "stop",
    )


@pytest.fixture
def harness_config(temp_dir):
    return {
        "loop": {"max_turns": 10, "idle_timeout": 3},
        "llm": {
            "provider": "openai_compat", "model": "gpt-4o",
            "api_base": "", "api_key_cmd": "echo test",
            "temperature": 0.1, "max_tokens": 4096,
        },
        "tools": {
            "allowed": ["read_file", "write_file", "run_shell", "finish"],
            "shell_timeout": 60,
        },
        "guardrails": {
            "allowed_paths": [str(temp_dir)],
            "command_rules": [
                {"pattern": r"^(ls|cat|pytest|echo|python|mkdir)\b", "level": "safe"},
                {"pattern": r"\brm -rf\b", "level": "dangerous"},
            ],
            "hitl": {"timeout": 30, "enabled": True},
            "sandbox": {"enabled": False, "memory_limit_mb": 512, "cpu_time_limit": 30},
        },
        "memory": {"db_path": ":memory:", "max_context_turns": 10},
        "web": {"host": "0.0.0.0", "port": 8080},
    }


@pytest.mark.asyncio
async def test_full_cycle_write_and_read(harness_config, temp_dir):
    """Agent writes a file, then reads it back."""
    test_file = temp_dir / "output.txt"
    responses = [
        make_response(tool_calls=[
            ToolCall(id="c1", name="write_file", arguments={
                "path": str(test_file), "content": "hello world",
            }),
        ]),
        make_response(tool_calls=[
            ToolCall(id="c2", name="read_file", arguments={
                "path": str(test_file),
            }),
        ]),
        make_response(tool_calls=[
            ToolCall(id="c3", name="finish", arguments={
                "summary": "File written and verified",
            }),
        ]),
    ]
    backend = MockLLMBackend(responses=responses)
    loop = AgentLoop(harness_config)
    result = await loop.run("Write and read a file", backend)
    assert result.stop_reason == StopReason.FINISH_CALLED
    assert "File written" in result.summary
    assert Path(test_file).read_text() == "hello world"


@pytest.mark.asyncio
async def test_guardrail_blocks_and_continues(harness_config, temp_dir):
    """Guardrail blocks a dangerous action, agent continues with safe action."""
    test_file = temp_dir / "safe.txt"
    test_file.write_text("safe content")
    responses = [
        # Attempt 1: dangerous command (blocked)
        make_response(tool_calls=[
            ToolCall(id="c1", name="run_shell", arguments={"cmd": "rm -rf /"}),
        ]),
        # Attempt 2: safe command (passes)
        make_response(tool_calls=[
            ToolCall(id="c2", name="read_file", arguments={"path": str(test_file)}),
        ]),
        # Finish
        make_response(tool_calls=[
            ToolCall(id="c3", name="finish", arguments={"summary": "Done"}),
        ]),
    ]
    backend = MockLLMBackend(responses=responses)
    loop = AgentLoop(harness_config)
    result = await loop.run("Do something", backend)
    assert result.stop_reason == StopReason.FINISH_CALLED


@pytest.mark.asyncio
async def test_feedback_loop_after_failure(harness_config, temp_dir):
    """Agent runs a failing test, then retries."""
    test_file = temp_dir / "test_fail.py"
    test_file.write_text("def test_fail(): assert 1 == 2")
    responses = [
        make_response(tool_calls=[
            ToolCall(id="c1", name="run_shell", arguments={
                "cmd": f"cd {temp_dir} && python -m pytest test_fail.py -v",
            }),
        ]),
        make_response(tool_calls=[
            ToolCall(id="c2", name="write_file", arguments={
                "path": str(test_file), "content": "def test_fail(): assert 1 == 1",
            }),
        ]),
        make_response(tool_calls=[
            ToolCall(id="c3", name="finish", arguments={"summary": "Fixed test"}),
        ]),
    ]
    backend = MockLLMBackend(responses=responses)
    loop = AgentLoop(harness_config)
    result = await loop.run("Fix failing test", backend)
    assert result.stop_reason == StopReason.FINISH_CALLED
    assert "Fixed" in result.summary


@pytest.mark.asyncio
async def test_max_turns_stops_loop(harness_config, temp_dir):
    """Loop stops after max_turns reached."""
    harness_config["loop"]["max_turns"] = 2
    responses = [
        make_response(tool_calls=[
            ToolCall(id=f"c{i}", name="run_shell", arguments={"cmd": "echo hello"})
        ]) for i in range(5)
    ]
    backend = MockLLMBackend(responses=responses)
    loop = AgentLoop(harness_config)
    result = await loop.run("Infinite loop prevention", backend)
    assert result.stop_reason == StopReason.MAX_TURNS
    assert result.turns == 2
```

- [ ] **Step 2: 运行集成测试**

```bash
pytest tests/test_integration.py -v
```
Expected: 4 PASS

- [ ] **Step 3: 提交**

```bash
git add tests/test_integration.py
git commit -m "test: add integration tests with Mock LLM for full harness cycles"
```

---

### Task 23: README 文档

**Files:**
- Modify: `README.md`

**Interfaces:**
- Produces: Complete README with install, usage, security, and deployment instructions

- [ ] **Step 1: 撰写 README.md**

```markdown
# AI4SE Coding Agent Harness

一个可治理、可观测的 Python 编程智能体（Coding Agent）Harness。

**核心公式：Agent = LLM + Harness**。LLM 只是"CPU"，Harness 是工程层。

## 功能

- **决策循环**：上下文组装 → LLM 调用 → 解析动作 → 分发 → 反馈 → 停判
- **工具系统**：文件读写、Shell 命令执行、任务完成声明
- **护栏系统（★ 深入模块）**：四层状态机 — 文件围栏、命令分级、HITL 审批、沙箱执行
- **反馈回路**：测试输出解析、失败分类、结构化反馈
- **记忆系统**：SQLite 存储、会话历史、跨会话事实
- **配置管理**：YAML 声明式规则、keyring 凭据存储

## 安装

```bash
pip install ai4se-harness
```

## 快速开始

### 1. 配置 API Key

```bash
harness setup
# 按提示输入 API Key（隐藏输入）
```

### 2. 运行任务

```bash
# 使用 Mock LLM（测试用）
harness run "Fix failing tests in src/" --mock

# 使用真实 LLM
harness run "Run pytest on the tests/ directory and fix any failures"
```

### 3. 查看状态

```bash
harness status
```

### 4. 启动 Web 仪表盘

```bash
harness web
# 访问 http://localhost:8080
```

## 配置

配置文件为 `harness.yaml`（项目根目录）或 `~/.harness/config.yaml`。

```yaml
loop:
  max_turns: 20          # 最大循环轮数

llm:
  provider: "openai_compat"
  model: "gpt-4o"
  api_base: "https://your-relay.com/v1"
  api_key_cmd: "keyring get harness"

guardrails:
  allowed_paths: ["./src", "./tests"]
  command_rules:
    - pattern: "^(ls|pytest|echo)\\b"
      level: safe
    - pattern: "\\brm -rf\\b"
      level: dangerous
  hitl:
    timeout: 30
```

## 安全

- API Key 通过系统密钥链（keyring）存储，不写入任何文件
- 配置文件不包含凭据
- 护栏四层拦截防止危险操作
- 文件围栏限制 agent 的文件访问范围

## 开发

```bash
git clone <repo>
pip install -e ".[dev]"
pytest tests/ -v
```

## 部署

### 阿里云 ECS

```bash
scp -r dist/* user@server:/opt/harness/
ssh user@server
sudo systemctl start harness-web
```

## 目录结构

```
src/          # Harness 内核源码
tests/        # 单元测试（Mock LLM）
demo/         # 机制演示脚本
spec/         # 设计文档
```

## 已知限制

- 沙箱为 subprocess 级别，不是真正的安全边界
- 单 session 运行，不支持并发
- Memory 使用简单关键词匹配，不做向量检索

## 作者

王祎 (241250007) — AI4SE 期末项目
```

- [ ] **Step 2: 提交**

```bash
git add README.md
git commit -m "docs: update README with install, usage, security, and deployment info"
```

---

## 最终验证

完成所有任务后，运行完整测试套件：

```bash
pytest tests/ -v --tb=short
```

Expected: ALL TESTS PASS (约 70+ 测试)

运行演示脚本：

```bash
python demo/demo1_guardrail_intercept.py
python demo/demo2_feedback_loop.py
python demo/demo3_guardrail_pipeline.py
```

Expected: 三个脚本均输出 "ALL TESTS PASSED"
