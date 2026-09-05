# Mini Agent Runtime

从零实现的最小可用 Agent Runtime：**不依赖** LangGraph / OpenHands / OpenClaw 等现成 Agent 框架。主循环、工具注册、LLM 输出解析、session 隔离、context 压缩均为本仓库自行实现。LLM 调用走 **OpenAI 兼容 HTTP API**（可用 OpenAI、DeepSeek、Moonshot、SiliconFlow、智谱等）。

## 运行方式

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
pip install -e ".[dev]"
copy .env.example .env
```

编辑 `.env`：

```
LLM_API_KEY=sk-...
LLM_BASE_URL=https://api.deepseek.com
LLM_MODEL=deepseek-chat
```

### CLI（推荐用来演示两个窗口）

```bash
# 窗口 1：查天气记待办
python -m mini_agent --user A --session window1

# 另开一个终端，窗口 2：写周报记待办
python -m mini_agent --user A --session window2
```

一次性提问：

```bash
python -m mini_agent --user A --session window1 "查北京天气并记待办：出门带伞"
```

### Web 双窗口

```bash
uvicorn mini_agent.server:app --reload --port 8000
```

打开 http://127.0.0.1:8000 ，左右两栏分别是用户 A 的 `window1` / `window2`。

### 测试

```bash
pytest -q
# 真实 LLM（需有效 LLM_API_KEY，且 LIVE_LLM=1 或 key 长度 >= 20）
pytest -q -m live
```

## 项目结构

```
mini-agent-runtime/
├── pyproject.toml              # 打包与 pytest 配置
├── .env.example                # LLM 配置模板（复制为 .env 使用，.env 不入库）
├── docs/
│   └── AI_PROMPT_AND_ISSUES.md # AI 辅助开发记录与问题解决
├── src/mini_agent/
│   ├── runtime.py              # Agent 主循环（Step 1–4，核心）
│   ├── parser.py               # LLM 输出解析：think / tool_calls / answer
│   ├── context.py              # 上下文组包与基础压缩（system prompt / 摘要）
│   ├── session.py              # 会话数据结构 + (user_id, session_id) 文件隔离
│   ├── llm.py                  # OpenAI 兼容 HTTP 客户端（可换 DeepSeek 等）
│   ├── tracing.py              # 工具与 LLM 调用 JSONL 日志（不进模型上下文）
│   ├── types.py                # 核心数据类型（ToolCall / ToolResult / ...）
│   ├── errors.py               # 异常层级
│   ├── cli.py / __main__.py    # CLI 入口（python -m mini_agent）
│   ├── server.py               # FastAPI Web 入口（双窗口演示）
│   ├── static_index.html       # Web 双窗口页面
│   └── tools/
│       ├── registry.py         # 工具注册机制：name + description + JSON Schema
│       ├── builtin.py          # 内置工具装配
│       ├── calculator.py       # 安全计算器（AST 白名单求值，不用 eval）
│       ├── search.py           # mock 检索
│       ├── weather.py          # mock 天气
│       └── todo.py             # 待办（状态挂 Session，按窗口隔离）
└── tests/                      # 26 个测试：25 个离线单测 + 1 个真实 LLM 联调
```

## 系统设计

```
用户输入
  → SessionStore.get_or_create(user_id, session_id)
  → ContextManager.build(system + 待办快照 + 旧轮摘要 + 近轮原文)
  → Loop (最多 N 轮)
        LLM.complete(messages)
        parse: think / tool_calls / answer
        若 tool_calls → ToolRegistry.execute → 把工具结果写入 session → continue
        若 answer     → 返回用户
        若超轮次     → MaxTurnsExceeded
  → 持久化 session + JSONL trace
```

核心模块：

| 模块 | 职责 |
| --- | --- |
| `runtime.py` | 自主实现的 Agent 循环（Step1–4） |
| `parser.py` | 从 LLM 文本提取 JSON：思考 / 工具调用 / 最终答案 |
| `tools/registry.py` | 工具注册：name + description + JSON Schema |
| `session.py` | `(user_id, session_id)` 文件级隔离 |
| `context.py` | 组包与基础压缩 |
| `tracing.py` | 工具与 LLM 调用日志（不进入模型上下文） |
| `llm.py` | OpenAI 兼容客户端 |

内置工具：`calculator`、`search`（mock 语料）、`weather`（mock）、`todo`（**按 session 隔离**）。

LLM 被要求输出：

```json
{"think": "...", "tool_calls": [{"name": "weather", "arguments": {"city": "北京"}}], "answer": null}
```

或最终：

```json
{"think": "...", "tool_calls": [], "answer": "给用户看的话"}
```

解析器兼容 markdown 代码块；若完全没有 JSON，则把原文当作最终回答，避免协议抖动导致循环卡死。

## Session 管理

- 主键：`(user_id, session_id)`。`session_id` 就是「窗口」。
- 用户 A 的 `window1` 与 `window2` 各有一份 JSON：消息、未完成待办、已完成待办、滚动摘要。
- 随时用同一个 `--user A --session window1` 续聊，不会读到 window2 的待办。

## Memory / Context：召回时机与放置方式

**始终放入（system）**

1. 工具 Schema：让模型按 schema 自己决定调不调、调哪个。
2. 当前 session 的待办快照（open + completed）：待办是跨轮状态，压缩后仍要能追问「刚才那个待办」。
3. `user_id` / `session_id`：减少串窗。

**按轮次追加（messages）**

| 信息 | 是否进 LLM context | 原因 |
| --- | --- | --- |
| 用户输入 | 是 | 任务与追问的唯一来源 |
| 工具执行结果 | 是（映射成 user 消息：`[工具结果 name]`） | 模型必须据此决定继续 loop 还是回答 |
| Agent 思考 `think` | 近轮保留，压缩时截断 | 有助于纯对话追问，但很长、噪声大，不值得全量常驻 |
| 最终 answer | 是 | 后续追问需要「上次说了什么」 |
| 工具 trace / 异常堆栈 | **否**，只写 `data/traces/*.jsonl` | 给调试和评分，不占 token |

**召回时机**

- 每一轮 LLM 调用前组包一次（包括工具后的下一跳）。
- 纯对话追问：依赖近轮 user/assistant 原文 + 待办快照。
- 带工具的追问：近轮工具结果仍在 recent window 内则原文可见；被挤出 recent 后，只通过摘要 + 待办快照召回。

**基础压缩（不做分层记忆 / embedding）**

- 只保留最近 `keep_recent_messages` 条原文。
- 更早的消息折叠成一段「此前对话摘要」system 消息，并写回 `session.summary`。
- 总字符超过 `CONTEXT_CHAR_BUDGET` 时，截断 think，再从最旧的 recent 消息开始丢弃。

## 异常处理

- 未知工具、非法计算器表达式、todo 缺参：变成 `ok=false` 的工具观察，送回模型让它改参数，而不是把整个进程打崩。
- LLM HTTP 失败：`LLMError`。
- 超过 `MAX_LOOP_TURNS`：`MaxTurnsExceeded`。
- 每次失败都记入 JSONL trace。

## 提交说明

本仓库即为题目要求的代码，已推送至 GitHub：

**仓库地址:https://github.com/<your-name>/mini-agent-runtime**（提交前替换为实际 URL）

真实 LLM：配置 `.env` 后运行 CLI / `pytest -m live`。
测试：`pytest -q`（离线，25 passed）；`pytest -m live`（真实 LLM，需有效 key）。
