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

### 从 GitHub Release 安装

```bash
pip install https://github.com/Delario17/SE-SummerBootCamp-FinalProject/releases/download/v0.1.0/ai4se_harness-0.1.0-py3-none-any.whl
```

### 从源码安装

```bash
git clone https://github.com/Delario17/SE-SummerBootCamp-FinalProject.git
cd SE-SummerBootCamp-FinalProject
pip install -e ".[dev]"
```

## 快速开始

### 1. 配置 API Key

```bash
harness setup
# 按提示输入 API Key（隐藏输入），自动存入系统密钥链
```

### 2. 运行任务

```bash
# 使用 Mock LLM（测试用，无需真实 API Key）
harness run "Fix failing tests in src/" --mock

# 使用真实 LLM
harness run "Run pytest on the tests/ directory and fix any failures"
```

### 3. 查看状态

```bash
harness status
```

## 使用示例

### 护栏拦截危险操作

```bash
echo 'rm -rf /' > /tmp/dangerous.sh
harness run "Execute /tmp/dangerous.sh" --mock
```

### 反馈回路驱动自我修正

```bash
harness run "Fix the failing test in tests/test_feedback.py" --mock
```

### 运行演示脚本

```bash
python demo/demo1_guardrail_intercept.py
python demo/demo2_feedback_loop.py
python demo/demo3_guardrail_pipeline.py
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
git clone https://github.com/Delario17/SE-SummerBootCamp-FinalProject.git
pip install -e ".[dev]"
pytest tests/ -v
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
