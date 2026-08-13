# SPEC.md — Coding Agent Harness

> **项目**：AI4SE 期末项目 · A 类 · Coding Agent Harness
> **学生**：王祎（241250007）
> **日期**：2026-08-07
> **版本**：v1.0

---

## 1. 问题陈述

### 1.1 要解决的问题

当前主流的编码智能体（如 Claude Code、GitHub Copilot、Cursor）虽然能力强大，但其运行机制对用户来说是黑盒——用户无法掌控智能体在何时执行何种操作、哪些操作被允许、如何验证智能体的行为是否正确。开发者在实际工程中需要的是一个**可治理、可观测、可验证**的编码智能体运行时，而非一个"把 prompt 丢进去等结果"的聊天界面。

### 1.2 核心命题

**Agent = LLM + Harness**。LLM 只是"CPU"，负责决定下一步做什么；Harness 是工程层，负责决策循环、工具分发、护栏拦截、反馈验证、记忆管理和配置加载。本项目的目标是构建这一 Harness 层，证明"当 LLM 能完成大部分思考时，工程师的价值在于 Harness 这层工程"。

### 1.3 目标用户

- 需要在 AI 辅助编码中保持安全边界的软件工程师
- 希望理解编码智能体内部机制的 AI4SE 研究者
- 需要在团队中统一管理 AI 编码行为规范的 Tech Lead

### 1.4 为什么值得做

- 现有编码智能体框架（LangChain AgentExecutor、AutoGen 等）将 Harness 逻辑封装在框架内部，用户无法定制
- 安全性（防止 AI 误删代码/数据库）是实际痛点，不是学术假设
- 本项目通过"用一个 Harness 构建另一个 Harness"的元认知过程，对 Superpowers 方法论形成第一手批判性理解

---

## 2. 用户故事

### US-1：开发者使用 CLI 完成编码任务
> 作为开发者，我可以通过 CLI 输入一个编码任务（如"在 src/ 下运行 pytest 并修复失败的测试"），让 Harness 自动规划、执行、验证，直到任务完成或达到最大轮数。

**验收标准**：输入任务描述 → Harness 自动调用 LLM → 执行工具 → 反馈验证 → 循环直到完成，输出最终结果。

### US-2：护栏自动拦截危险操作
> 作为开发者，当 Harness 尝试执行 `rm -rf /` 或删除数据库等危险命令时，系统应自动拦截并告知我原因，不执行该命令。

**验收标准**：任意危险命令被护栏拦截，执行被拒绝，日志记录拦截原因。

### US-3：HITL 审批高风险操作
> 作为开发者，当 Harness 尝试执行 `git push --force` 等高风险命令时，系统应暂停等待我的人工确认，我可以选择同意或拒绝。若我 30 秒内未响应，系统自动拒绝。

**验收标准**：高风险命令触发 HITL 暂停 → 输入 y 执行 / 输入 n 拒绝 / 超时自动拒绝。

### US-4：文件系统围栏限制访问范围
> 作为开发者，我可以配置 Harness 只能操作指定目录（如 `./src` 和 `./tests`），任何越界读写都应被拒绝。

**验收标准**：配置白名单路径后，尝试读取 `/etc/passwd` 或写入 `/usr/bin/` 均被文件围栏拦截。

### US-5：Web 仪表盘查看运行状态
> 作为开发者，我可以通过浏览器打开 Web 仪表盘，查看当前 Harness 的运行状态、最近的工具调用历史、护栏拦截记录，以及待处理的 HITL 审批。

**验收标准**：Web 页面实时显示 session 状态、工具调用日志、护栏拦截记录；HITL 审批界面可交互。

### US-6：反馈回路驱动自我修正
> 作为开发者，当 Harness 执行的测试失败时，系统应自动解析失败原因，将其反馈给 LLM，让 LLM 基于失败信息重新生成修正方案。

**验收标准**：注入测试失败 → 反馈回路解析失败信息 → LLM 收到失败信息 → 修改代码 → 重新测试 → 通过。

### US-7：配置声明式规则
> 作为开发者，我可以通过 YAML 配置文件声明护栏规则、允许的工具列表、最大循环轮数等，无需修改代码。

**验收标准**：修改 `harness.yaml` 中的 `max_turns: 3` → Harness 在 3 轮后自动停止。

---

## 3. 功能规约

### 3.1 模块划分

| 模块 | 路径 | 职责 |
|------|------|------|
| 主循环 | `src/loop/` | 上下文组装 → LLM 调用 → 解析 → 分发 → 反馈 → 停判 |
| 工具系统 | `src/tools/` | 工具 Schema 定义、参数校验、执行调度 |
| 护栏系统 | `src/guardrails/` | **深入模块**：文件围栏、命令分级、HITL、沙箱 |
| 反馈回路 | `src/feedback/` | 测试输出解析、失败分类、结构化反馈生成 |
| 记忆系统 | `src/memory/` | SQLite 存储、会话历史、简单检索 |
| 配置管理 | `src/config/` | YAML 加载、规则校验、凭据获取 |
| LLM 抽象 | `src/llm/` | OpenAI 兼容适配器、Mock 实现 |

### 3.2 主循环（Agent Loop）

**输入**：用户任务描述（字符串）
**行为**：
1. 加载配置（`harness.yaml`）
2. 从 Memory 检索相关上下文
3. 组装消息列表（system prompt + 上下文 + 当前任务 + 历史）
4. 调用 LLM（`llm.chat(messages, tools)`）
5. 解析 LLM 响应：
   - 若返回 `tool_calls`：提取工具名 + 参数
   - 若返回纯文本：视为最终回复，进入停止判断
6. 护栏检查（`guardrails.check(action)`）
   - 若拦截：记录原因，将拒绝信息注入反馈
   - 若需 HITL：暂停等待用户确认
   - 若通过：继续
7. 工具分发执行（`tools.dispatch(name, params)`）
8. 收集执行结果（stdout, stderr, exit_code）
9. 反馈回路分析结果（`feedback.analyze(result)`）
10. 将反馈注入上下文，回到步骤 3
11. 停止条件：(a) LLM 返回 finish 工具调用 (b) 达到 max_turns (c) 护栏连续拦截 3 次

**输出**：最终结果（成功/失败 + 摘要）

**边界条件**：
- LLM 返回格式异常 → 重试 1 次，仍失败则终止
- 工具执行超时（默认 60s）→ 终止该次执行，注入超时反馈
- 空闲轮数（LLM 连续 3 轮不调用工具）→ 终止

### 3.3 工具系统

**工具定义**（JSON Schema 格式）：

| 工具名 | 参数 | 描述 |
|--------|------|------|
| `read_file` | `path: str` | 读取文件内容 |
| `write_file` | `path: str, content: str` | 写入或创建文件 |
| `run_shell` | `cmd: str, cwd: str (optional)` | 执行 shell 命令 |
| `finish` | `summary: str` | 声明任务完成 |

**工具分发器**：
- 接收 `ToolCall(name, params)` → 校验参数类型 → 返回 `ToolResult`
- 每个工具是独立函数，参数校验通过 JSON Schema 验证
- 所有工具执行均通过护栏检查

**错误处理**：
- 文件不存在 → 返回错误信息（不抛异常）
- 命令执行失败 → 返回 exit_code + stderr
- 参数校验失败 → 返回校验错误，不执行

### 3.4 护栏系统（★ 深入模块）

#### 3.4.1 文件系统围栏（第1层）

**功能**：限制 agent 的文件读写范围。

**机制**：
- 读取 `config.guardrails.allowed_paths`（路径列表，如 `["./src", "./tests", "./demo"]`）
- 所有 `read_file`/`write_file` 操作前，将目标路径解析为绝对路径
- 检查绝对路径是否以任一白名单路径为前缀
- 不匹配 → 拦截，返回 `GuardrailResult(blocked=True, reason="...")`

**确定性的单测验证**：
```python
def test_file_fence_blocks_outside_access():
    fence = FileFence(allowed_paths=["./src", "./tests"])
    assert fence.check("read", "/etc/passwd").blocked == True
    assert fence.check("write", "./src/main.py").blocked == False
```

#### 3.4.2 命令分级（第2层）

**功能**：将 shell 命令分为三个级别。

**机制**：
- 规则配置在 `guardrails.yaml` 中，每项包含 `pattern`（正则）和 `level`（safe/warn/dangerous）
- 默认规则：
  - `safe`：`ls`, `cat`, `pytest`, `flake8`, `mypy`, `python`, `pip`, `git status`, `git diff`, `echo`, `mkdir`, `touch`
  - `warn`：`git commit`, `git checkout`, `git branch`, `pip install`, `npm install`
  - `dangerous`：`rm -rf`, `DROP TABLE`, `DELETE FROM`, `git push --force`, `chmod 777`, `sudo`, `> /dev/`, `mkfs`, `dd if=`
- 匹配逻辑：遍历规则，返回第一个匹配的级别

**确定性的单测验证**：
```python
def test_command_classifier_flags_dangerous():
    classifier = CommandClassifier.from_config("guardrails.yaml")
    assert classifier.classify("rm -rf /") == CommandLevel.DANGEROUS
    assert classifier.classify("pytest tests/") == CommandLevel.SAFE
```

#### 3.4.3 HITL 人机交互（第3层）

**功能**：对 `dangerous` 级别的命令暂停执行，等待人工确认。

**机制**：
- 触发条件：命令分级结果为 `dangerous`
- 暂停流程：
  1. 向用户展示命令内容 + 风险说明
  2. 等待用户输入 `y`（同意）/ `n`（拒绝）
  3. 超时时间（默认 30s）内无响应 → 自动拒绝
  4. 记录审批结果到审计日志
- CLI 模式：`input()` 等待终端输入
- Web 模式：在仪表盘中显示待审批项，等待用户点击

**确定性的单测验证**：
```python
@pytest.mark.asyncio
async def test_hitl_approves_on_yes():
    hitl = HITLGuard(input_func=lambda _: "y", timeout=30)
    result = await hitl.request_approval(Action("rm -rf ./tmp"))
    assert result.approved == True

@pytest.mark.asyncio
async def test_hitl_rejects_on_timeout():
    hitl = HITLGuard(input_func=lambda _: None, timeout=0.1)  # 立即超时
    result = await hitl.request_approval(Action("rm -rf ./tmp"))
    assert result.approved == False
    assert result.reason == "timeout"
```

#### 3.4.4 沙箱执行（第4层，可选）

**功能**：在受限环境中执行危险命令。

**机制**：
- 使用 `subprocess` 在临时目录中执行
- 限制：
  - `cwd` 设为临时目录
  - 设置环境变量 `PATH` 为最小集合
  - 设置 `timeout` 限制执行时间
  - 设置 `resource` 限制内存/CPU
- 注意：Python 的 `subprocess` 无法做到真正的 OS 级沙箱（如 Docker），本层为尽力而为的软件限制

**确定性的单测验证**：
```python
@pytest.mark.asyncio
async def test_sandbox_restricts_network():
    sandbox = SandboxExecutor()
    result = await sandbox.execute("curl https://example.com")
    # 在受限环境中，curl 应失败（网络不可达或超时）
    assert result.exit_code != 0
```

#### 3.4.5 护栏状态机总览

```
用户动作请求
     │
     ▼
┌─────────────┐   拦截    ┌──────────┐
│ 第1层：文件围栏│ ──────→ │ 拒绝执行   │
│ 路径白名单检查 │         │ 返回原因   │
└──────┬──────┘         └──────────┘
       │ 通过
       ▼
┌─────────────┐
│ 第2层：命令分级│
│ 安全/警告/危险 │
└──────┬──────┘
       │
   ┌───┼───┐
   ▼   ▼   ▼
 安全  警告  危险
   │   │   │
   │   │   └──→ ┌──────────────┐
   │   │        │ 第3层：HITL   │
   │   │        │ 暂停→人工审批  │
   │   │        │ 超时→自动拒绝  │
   │   │        └──────┬───────┘
   │   │           ✓通过  ✗拒绝
   │   │            │      │
   ▼   ▼            ▼      ▼
┌──────────────┐  ┌──────────┐
│ 第4层：沙箱执行│  │  拒绝执行  │
│ (可选)       │  │  记录审计  │
└──────────────┘  └──────────┘
```

### 3.5 反馈回路

**功能**：解析执行结果，生成结构化反馈，注入 LLM 上下文。

**输入**：`ToolResult(stdout, stderr, exit_code, tool_name)`

**处理流程**：
1. **输出解析器**：根据工具类型选择解析策略
   - `run_shell` 且命令为 `pytest`：解析 pytest 输出（通过/失败/错误数/失败详情）
   - `run_shell` 且命令为 `flake8`：解析 lint 输出（文件/行号/错误码）
   - 其他：返回原始 stdout/stderr 摘要
2. **失败分类器**：
   - `SYNTAX_ERROR`：语法错误 → 建议修正语法
   - `ASSERTION_FAILURE`：断言失败 → 建议检查逻辑
   - `IMPORT_ERROR`：导入错误 → 建议安装依赖
   - `TIMEOUT`：超时 → 建议优化或拆分
   - `UNKNOWN`：未知错误 → 传递原始错误信息
3. **结构化反馈生成**：生成 `Feedback(type, summary, detail, suggestion)`

**确定性的单测验证**：
```python
def test_parse_pytest_failure():
    stdout = """
    tests/test_main.py::test_add FAILED
    AssertionError: assert 3 == 5
    ======= 1 failed, 2 passed in 0.5s =======
    """
    feedback = FeedbackParser.parse("run_shell", stdout, "", 1)
    assert feedback.type == FeedbackType.ASSERTION_FAILURE
    assert feedback.failed_count == 1
    assert "test_add" in feedback.detail
```

### 3.6 记忆系统

**功能**：存储和检索跨轮次、跨会话的信息。

**存储模型**：
- `sessions` 表：`(id, created_at, task_description)`
- `messages` 表：`(id, session_id, turn, role, content, tool_calls, tool_results, created_at)`
- `facts` 表：`(id, key, value, source, created_at)` — 跨会话持久化事实

**检索策略**：
- 当前会话：按 `session_id` 获取所有消息，按 `turn` 排序
- 相关事实：按 `key` 关键词匹配（简单 `LIKE` 查询，不引入向量检索）
- 组装上下文：取最近 N 轮消息 + 相关事实，控制在 token 预算内

**接口**：
- `memory.create_session(task) -> session_id`
- `memory.add_message(session_id, turn, message)`
- `memory.get_context(session_id, max_turns=10) -> list[Message]`
- `memory.save_fact(key, value)`
- `memory.search_facts(query) -> list[Fact]`

### 3.7 配置管理

**配置文件**：`harness.yaml`（项目根目录或 `~/.harness/config.yaml`）

**结构**：
```yaml
loop:
  max_turns: 20          # 最大循环轮数
  idle_timeout: 3        # 连续空闲轮数后终止

llm:
  provider: "openai_compat"
  model: "gpt-4o"        # 或中转站对应模型名
  api_base: "https://your-relay.com/v1"
  api_key_cmd: "keyring get harness"  # 凭据获取命令
  temperature: 0.1
  max_tokens: 4096

tools:
  allowed: ["read_file", "write_file", "run_shell", "finish"]
  shell_timeout: 60      # 命令执行超时（秒）

guardrails:
  allowed_paths: ["./src", "./tests", "./demo", "./spec"]
  command_rules:
    - pattern: "^(ls|cat|pytest|flake8|mypy|python|pip|git status|git diff|echo|mkdir|touch)\\b"
      level: safe
    - pattern: "^(git commit|git checkout|git branch|pip install|npm install)\\b"
      level: warn
    - pattern: "\\brm -rf\\b|\\bDROP TABLE\\b|\\bDELETE FROM\\b|git push --force|chmod 777|\\bsudo\\b|/dev/null|\\bmkfs\\b|\\bdd if="
      level: dangerous
  hitl:
    timeout: 30           # HITL 超时（秒）
    enabled: true
  sandbox:
    enabled: false        # 沙箱默认关闭
    memory_limit_mb: 512
    cpu_time_limit: 30

memory:
  db_path: "~/.harness/memory.db"
  max_context_turns: 10

web:
  host: "0.0.0.0"
  port: 8080
```

**凭据安全**：
- `api_key` 绝不写入配置文件
- 通过 `api_key_cmd` 指定获取命令（如 `keyring get harness` 或 `cat ~/.harness/.token`）
- 首次运行：引导用户输入 key → 存入系统密钥链（通过 `keyring` 库）

---

## 4. 非功能性需求

### 4.1 性能
- Mock LLM 模式下，单轮循环 < 100ms
- 真实 LLM 模式下，单轮循环耗时取决于 API 响应时间（通常 1-5s）
- CLI 启动时间 < 1s
- Web 仪表盘页面加载 < 2s

### 4.2 安全（含凭据威胁模型）

**威胁模型**：
| 威胁 | 风险等级 | 对策 |
|------|---------|------|
| API Key 泄露到 git | 高 | key 不写入任何文件，通过 keyring 获取；`.gitignore` 排除 `.harness/` |
| API Key 在进程列表中可见 | 中 | 不通过环境变量/命令行参数传递 key；直接从 keyring 读取 |
| Agent 执行危险命令 | 高 | 护栏四层拦截：围栏 + 分级 + HITL + 沙箱 |
| Agent 读取敏感文件 | 高 | 文件围栏白名单限制 |
| 日志泄露 key | 中 | 日志中过滤 key 模式（`sk-...`）替换为 `***` |
| 内存转储泄露 key | 低 | key 使用后立即从内存清除（`del key`） |

**凭据管理流程**：
1. 首次运行：`harness setup` → 提示输入 API Key（隐藏输入） → 存入系统密钥链（service="harness", username="api_key"）
2. 运行时：`harness run "task"` → 通过 `keyring.get_password("harness", "api_key")` 获取 → 使用后立即清除
3. 查看状态：`harness status` → 显示 `API Key: **** (keyring)` 不显示明文
4. 更新：`harness setup --reset` → 覆盖旧 key
5. 清除：`harness setup --clear` → 删除 keyring 中的 key

### 4.3 可用性
- CLI 提供清晰的 help 信息（`harness --help`）
- 错误信息包含可操作的建议（如"护栏拦截：rm -rf / 不在允许路径内"）
- Web 仪表盘直观展示运行状态，无需文档即可理解

### 4.4 可观测性
- 所有护栏拦截事件记录到审计日志
- 每轮循环的工具调用和结果记录到消息历史
- Web 仪表盘实时展示最近 N 条事件

---

## 5. 系统架构

### 5.1 组件图

```
┌─────────────────────────────────────────────────────────┐
│                    CLI (click)                           │
│  harness run "task" | harness setup | harness web        │
├─────────────────────────────────────────────────────────┤
│                  Web 仪表盘 (FastAPI)                     │
│  GET / → 状态页面 | GET /api/history → 历史              │
│  POST /api/hitl/{id}/approve|reject → HITL 审批          │
├─────────────────────────────────────────────────────────┤
│                   Agent 主循环 (Loop)                     │
│  ┌──────────────────────────────────────────────────┐  │
│  │  assemble_context → llm.chat → parse → guardrail │  │
│  │       → dispatch → feedback → stop_check         │  │
│  └──────────────────────────────────────────────────┘  │
├──────────┬──────────┬──────────┬──────────┬─────────────┤
│  Tools   │Guardrails│ Feedback │  Memory  │   Config    │
│  Schema  │ 围栏     │ 解析器   │  SQLite  │   YAML      │
│  校验    │ 分级     │ 分类器   │  检索    │   校验      │
│  执行    │ HITL     │ 生成器   │          │   keyring   │
│          │ 沙箱     │          │          │             │
├──────────┴──────────┴──────────┴──────────┴─────────────┤
│              LLM 抽象层 (Protocol)                        │
│     ┌──────────────────┐  ┌──────────────────┐          │
│     │ OpenAICompat     │  │ MockLLM          │          │
│     │ Backend          │  │ Backend          │          │
│     └──────────────────┘  └──────────────────┘          │
└─────────────────────────────────────────────────────────┘
```

### 5.2 数据流

```
User Input (CLI/Web)
       │
       ▼
┌──────────┐     ┌──────────┐     ┌──────────┐
│  Config  │────→│  Memory  │────→│  Loop    │
│  加载规则  │     │  检索上下文 │     │  组装消息  │
└──────────┘     └──────────┘     └────┬─────┘
                                       │
                                       ▼
                                 ┌──────────┐
                                 │   LLM    │
                                 │  chat()  │
                                 └────┬─────┘
                                      │
                            ┌─────────┼─────────┐
                            ▼                    ▼
                      tool_calls            text/finish
                            │                    │
                            ▼                    ▼
                      ┌──────────┐         ┌──────────┐
                      │Guardrails│         │  Stop    │
                      │  检查    │         │  Check   │
                      └────┬─────┘         └──────────┘
                           │
              ┌────────────┼────────────┐
              ▼            ▼            ▼
           拦截          HITL         通过
              │            │            │
              ▼            ▼            ▼
         拒绝执行      人工审批      ┌──────────┐
         记录日志      超时/同意/拒绝  │  Tools   │
                                    │  执行    │
                                    └────┬─────┘
                                         │
                                         ▼
                                   ┌──────────┐
                                   │ Feedback │
                                   │  分析    │
                                   └────┬─────┘
                                        │
                                        ▼
                                  回到 Loop (下一轮)
```

### 5.3 外部依赖
- **LLM 提供商**：OpenAI 兼容中转站 API（HTTP/HTTPS）
- **系统密钥链**：macOS Keychain / Windows Credential Manager / Linux Secret Service（通过 `keyring` 库）
- **无**：不依赖任何外部数据库、消息队列或云服务（记忆使用本地 SQLite）

---

## 6. 数据模型

### 6.1 核心实体

```python
@dataclass
class Message:
    role: Literal["system", "user", "assistant", "tool"]
    content: str | None
    tool_calls: list[ToolCall] | None
    tool_call_id: str | None
    name: str | None

@dataclass
class ToolCall:
    id: str
    name: str                      # "read_file" | "write_file" | "run_shell" | "finish"
    arguments: dict[str, Any]       # 工具参数

@dataclass
class ToolResult:
    tool_call_id: str
    tool_name: str
    success: bool
    stdout: str
    stderr: str
    exit_code: int
    duration_ms: float

@dataclass
class GuardrailResult:
    allowed: bool
    level: str                     # "safe" | "warn" | "dangerous"
    reason: str | None
    requires_hitl: bool
    blocked: bool

@dataclass
class Feedback:
    type: FeedbackType              # SYNTAX_ERROR | ASSERTION_FAILURE | IMPORT_ERROR | TIMEOUT | UNKNOWN
    summary: str
    detail: str
    suggestion: str
    failed_count: int
    passed_count: int

@dataclass
class LLMResponse:
    content: str | None
    tool_calls: list[ToolCall] | None
    finish_reason: str             # "stop" | "tool_calls" | "length"
    usage: dict[str, int] | None

@dataclass
class Session:
    id: str                         # UUID
    task: str
    status: str                     # "running" | "completed" | "error" | "stopped"
    turns: int
    created_at: datetime
    completed_at: datetime | None
```

### 6.2 数据库表

```sql
CREATE TABLE sessions (
    id TEXT PRIMARY KEY,
    task TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'running',
    turns INTEGER DEFAULT 0,
    created_at TEXT NOT NULL,
    completed_at TEXT
);

CREATE TABLE messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    turn INTEGER NOT NULL,
    role TEXT NOT NULL,
    content TEXT,
    tool_calls TEXT,       -- JSON
    tool_results TEXT,     -- JSON
    created_at TEXT NOT NULL,
    FOREIGN KEY (session_id) REFERENCES sessions(id)
);

CREATE TABLE facts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    key TEXT NOT NULL UNIQUE,
    value TEXT NOT NULL,
    source TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT,
    event_type TEXT NOT NULL,    -- "guardrail_block" | "hitl_approve" | "hitl_reject" | "hitl_timeout" | "tool_execute"
    detail TEXT NOT NULL,        -- JSON
    created_at TEXT NOT NULL
);
```

---

## 7. 凭据与分发设计

### 7.1 凭据存储方案

- **方案**：Python `keyring` 库，跨平台密钥链
- **存储位置**：
  - macOS：Keychain
  - Windows：Credential Manager
  - Linux：Secret Service / `keyrings.cryptfile`（加密文件回退）
- **Service name**：`harness`
- **Username**：`api_key`
- **录入流程**：`harness setup` → 隐藏输入 → `keyring.set_password("harness", "api_key", key)`
- **更新**：`harness setup --reset`
- **清除**：`harness setup --clear`
- **查看状态**：`harness status` → 显示 `API Key: **** (stored in keyring)`，不显示明文

### 7.2 分发方案

- **形态**：PyPI 包
- **包名**：`ai4se-harness`
- **安装**：`pip install ai4se-harness`
- **入口点**：`harness` CLI 命令
- **构建**：`pyproject.toml` + `setuptools`
- **目标平台**：macOS、Linux、Windows（Python 3.11+）
- **依赖**：`openai`, `pyyaml`, `keyring`, `click`, `fastapi`, `uvicorn`, `jinja2`, `pydantic`
- **已知限制**：需要 Python 3.11+；Linux 系统密钥链需要 `secret-service` 或使用加密文件回退

### 7.3 云部署

- **平台**：阿里云 ECS
- **Web 服务**：FastAPI + uvicorn，通过 `systemd` 管理
- **反向代理**：Nginx
- **访问方式**：公网 IP + 端口 或 绑定域名
- **启动**：`systemctl start harness-web`
- **CI/CD**：GitHub Actions 构建 PyPI 包 + SSH 部署到 ECS

---

## 8. 技术选型与理由

| 组件 | 选择 | 版本 | 理由 |
|------|------|------|------|
| 语言 | Python | 3.11+ | 生态丰富，openai SDK 最成熟，keyring 跨平台支持好，开发速度快 |
| LLM SDK | `openai` | ≥1.0 | 中转站兼容 OpenAI 格式，官方 SDK 稳定 |
| 异步框架 | `asyncio` | 标准库 | 原生支持，零额外依赖，IO 密集场景（API 调用）足够 |
| HTTP 客户端 | `httpx` | ≥0.25 | 异步支持，openai SDK 底层依赖 |
| 测试框架 | `pytest` + `pytest-asyncio` | ≥7.0 | Python 标准测试框架，异步测试支持好 |
| 配置解析 | `pyyaml` | ≥6.0 | YAML 标准库 |
| 数据库 | `sqlite3` | 标准库 | 零依赖，适合单机、轻量存储 |
| Web 框架 | `FastAPI` | ≥0.100 | 异步原生、自动生成 OpenAPI 文档、轻量 |
| 模板引擎 | `Jinja2` | ≥3.0 | FastAPI 默认推荐，简单够用 |
| 数据校验 | `pydantic` | ≥2.0 | FastAPI 依赖，用于配置和数据结构校验 |
| CLI 框架 | `click` | ≥8.0 | 简洁、Pythonic，比 argparse 更好用 |
| 凭据存储 | `keyring` | ≥24.0 | 跨平台密钥链，无需额外配置 |
| 分发 | `setuptools` + `pyproject.toml` | — | PyPI 标准打包方式 |
| Web 服务器 | `uvicorn` | ≥0.20 | FastAPI 推荐，异步 ASGI 服务器 |
| 部署 | 阿里云 ECS + Nginx + systemd | — | 学生可用，公网访问，成本低 |

**不使用的框架**：LangChain、AutoGen、CrewAI、LlamaIndex——这些是"寄生于框架"的典型，违反 §A.4 的纪律要求。

---

## 9. 验收标准

### 9.1 核心功能验收

| 编号 | 验收项 | 验证方式 | 标准 |
|------|--------|---------|------|
| AC-1 | Mock LLM 下主循环完整运行 | 单测 | 注入预定响应序列，断言循环正确执行并停止 |
| AC-2 | 工具分发正确执行 | 单测 | 注入 `write_file` tool_call → 断言文件创建 |
| AC-3 | 文件围栏拦截越界访问 | 单测 | 注入 `read_file("/etc/passwd")` → 断言被拦截 |
| AC-4 | 命令分级正确分类 | 单测 | `rm -rf /` → dangerous, `pytest` → safe |
| AC-5 | HITL 审批通过/拒绝/超时 | 单测 | 注入不同输入 → 断言对应结果 |
| AC-6 | 反馈回路解析测试失败 | 单测 | 注入 pytest 失败输出 → 断言正确解析 |
| AC-7 | 记忆读写和检索 | 单测 | 写入消息 → 检索 → 断言内容一致 |
| AC-8 | 配置加载和校验 | 单测 | 修改 `max_turns: 3` → 断言循环 3 轮后停止 |

### 9.2 机制演示验收

| 编号 | 演示场景 | 验证方式 |
|------|---------|---------|
| MD-1 | 护栏拦截危险动作 | 演示脚本：注入 `rm -rf /` → 护栏拦截 → 记录到审计日志 |
| MD-2 | 反馈回路驱动自我修正 | 演示脚本：注入测试失败 → 反馈解析 → LLM 收到失败信息 → 修改代码 → 重测通过 |
| MD-3 | 护栏状态机完整流程 | 演示脚本：文件围栏 → 命令分级 → HITL 审批 → 沙箱执行，展示四层协同 |

### 9.3 部署验收

| 编号 | 验收项 | 标准 |
|------|--------|------|
| DP-1 | PyPI 安装 | `pip install ai4se-harness` 成功，`harness --help` 正常 |
| DP-2 | Web 仪表盘可访问 | 浏览器打开公网地址，能看到状态页面 |
| DP-3 | 凭据安全录入 | `harness setup` 引导输入 key，`harness status` 不显示明文 |
| DP-4 | CI 绿色 | `.gitlab-ci.yml` 中 `unit-test` job 最后一次运行通过 |

---

## 10. 风险与未决问题

### 10.1 风险

| 风险 | 影响 | 概率 | 缓解措施 |
|------|------|------|---------|
| 中转站 API 不稳定 | 真实 LLM 演示失败 | 中 | 核心功能全部用 Mock LLM 测试，演示脚本可以不依赖真实 API |
| Python 沙箱隔离不足 | 沙箱层无法真正限制恶意命令 | 高 | 文档明确说明沙箱为"软件级尽力而为"，不是安全边界；真正的隔离需要 Docker |
| 时间不足 | 某些模块简陋 | 中 | 坚持"最小实现"原则，非深入模块只做 MVP |
| keyring 在某些 Linux 环境不可用 | 凭据存储失败 | 低 | 提供加密文件回退方案（`keyrings.cryptfile`） |
| Web 仪表盘与 CLI 状态同步 | 两个入口操作同一 session 时冲突 | 低 | 使用 SQLite 作为共享状态，读写加锁 |

### 10.2 未决问题

1. **中转站的具体 API base URL 和模型名**：需要用户提供，在 `harness.yaml` 中配置
2. **Web 仪表盘是否需要认证**：如果没有认证，任何知道公网 IP 的人都能审批 HITL 请求。考虑到安全要求，建议加入简单的 Token 认证
3. **是否需要支持多 session 并发**：当前设计为单 session，多 session 并发需要更复杂的状态管理
4. **沙箱是否需要 Docker 实现**：当前为 subprocess 级别，若要求真正的隔离，可以后续添加 Docker 沙箱模式

---

## 11. 领域与机制设计（§A.5 额外要求）

### 11.1 领域分析：Coding 场景

**反馈信号**：
- 测试结果（pytest/flake8/mypy 输出）是最客观的反馈信号——通过/失败是确定的，失败位置是精确的
- 退出码（0 = 成功，非 0 = 失败）是二值信号
- 编译/类型检查错误是语法级别的确定信号

**危险动作**：
- 破坏性命令：`rm -rf`、`DROP TABLE`、`DELETE FROM`、`git push --force`、`chmod 777`、`sudo`
- 越界访问：读取系统文件（`/etc/passwd`、`~/.ssh/`）、写入系统目录（`/usr/bin/`）
- 对外发布：`git push`、`npm publish`、`docker push`

**所需工具**：
- 文件操作：`read_file`、`write_file`
- 命令执行：`run_shell`（用于运行测试、lint、构建）
- 任务管理：`finish`（声明完成）

**记忆需求**：
- 当前会话的对话历史（用于上下文连贯）
- 项目约定（如代码风格、测试框架）
- 历史决策（如"之前选择了方案 A 而非 B"）

### 11.2 重点维度：治理/护栏

**为什么选择治理/护栏作为深入维度**：

1. **天然适合用代码实现**：护栏的每一层都是确定性逻辑——路径匹配、正则匹配、超时判断。这些完全不依赖 LLM 的"智能"，是纯工程代码。
2. **最适合 mock LLM 单测**：护栏的每个判断都可以通过构造输入 → 断言输出来验证。不需要 LLM 参与，不需要网络。
3. **工程深度足够**：四层状态机（围栏 → 分级 → HITL → 沙箱）构成了完整的防御纵深，每层有独立的配置、独立的测试、独立的错误处理。
4. **实际价值最高**：AI 编码的安全性是最真实的痛点，不是学术假设。

### 11.3 机制编码实现方案

**护栏核心接口**：
```python
class Guardrail(Protocol):
    async def check(self, action: Action) -> GuardrailResult:
        """检查一个 action，返回是否允许、级别、原因"""
        ...

class GuardrailPipeline:
    """四层护栏管道，按顺序执行，任一拦截即停止"""
    def __init__(self, layers: list[Guardrail]):
        self.layers = layers

    async def check(self, action: Action) -> GuardrailResult:
        for layer in self.layers:
            result = await layer.check(action)
            if result.blocked:
                return result
        return GuardrailResult(allowed=True, level="safe")
```

**每层护栏都是独立的 `Guardrail` 实现**：
- `FileFence`：路径白名单
- `CommandClassifier`：正则分级
- `HITLGuard`：人机交互审批
- `SandboxExecutor`：沙箱执行

**所有护栏的可配置性**：规则通过 `guardrails.yaml` 声明式配置，用户可以在不修改代码的情况下添加/修改规则。

**所有护栏的可测试性**：每层护栏都可以用 mock LLM 做确定性单测——传入构造的 `Action`，断言 `GuardrailResult`。

---

> **本 SPEC 对应的项目文件**：
> - `AI4SE_Final_Project_A_Coding_Agent_Harness.md`（A 类项目要求）
> - `AI4SE_Final_Project_requirements.md`（通用要求）
> - 本文件为完整 SPEC，包含通用要求 §4.2 的 10 个标准章节 + A 类项目要求的「领域与机制设计」章节