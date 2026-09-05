# AI Prompt 与问题解决记录

本项目允许使用 AI 辅助开发，但 Agent 主循环未使用 LangGraph / OpenHands / OpenClaw。以下记录关键 Prompt 与实际踩坑。

## 1. 总体实现 Prompt

> 从零实现最小 Agent Runtime：不要用 LangGraph。循环为 用户输入 → 解析是回复还是调工具 → 执行工具 → 根据结果继续 loop 或返回。工具需注册 name/description/JSON Schema。解析 LLM 输出中的 think、tool_calls、answer。Session 按 (user_id, session_id) 隔离。Context 要能追问，过长做廉价压缩。给 pytest。LLM 走 OpenAI 兼容 API。

落地取舍：

- 协议用 **单一 JSON**，比 ReAct 纯文本正则更稳，也方便测试里塞 ScriptedLLM。
- 工具结果以 `role=tool` 存 session，发给模型时改写成 `[工具结果 name]` 的 user 消息，避免部分兼容网关不支持 `tool` role。

## 2. 解析器 Prompt

> 写一个解析函数：优先从 markdown fence 或全文里取 JSON；字段 think / tool_calls / answer；没有 JSON 时把原文当最终答案。

问题：真实模型偶尔在 JSON 前加「好的，我来调用工具」。  
解决：先扫 ```json fence，再 `find('{')` 到最后一个 `}`。

问题：有工具调用时模型仍填了 answer。  
解决：runtime **只要 tool_calls 非空就忽略 answer**，强制继续 loop，避免「边调工具边提前结束」。

## 3. Session 隔离 Prompt

> 用户 A 两个窗口：一个天气+待办，一个周报+待办，互相不能看见。

问题：如果 todo 做成进程内全局 list，测试会绿、演示会串窗。  
解决：`TodoTool.execute(..., session)` 把 todos 写在 **Session 对象** 上，随 JSON 文件落盘。主键目录：`data/sessions/{user}/{session}.json`。

## 4. Context 该塞什么

问过模型的问题：

> 用户输入、工具结果、思考过程，哪些进 context？压缩怎么做才够题目但不做向量库？

结论（已写进 README）：

- 必进：用户输入、工具结果、近轮 answer、工具 schema、当前待办快照。
- 选进且可截断：think。
- 不进模型：JSONL trace、Python 堆栈。
- 压缩：recent window + 旧轮摘要 + 超预算丢最旧 recent。不做 embedding。

问题：只靠对话压缩后，「把刚才的待办勾掉」会丢。  
解决：待办快照永远在 system，相当于结构化 working memory。

## 5. 测试不打真实 API

> 用可脚本化的假 LLM，按顺序返回 JSON，覆盖：直接回复、工具后回复、双工具、双 session、纯对话追问、工具追问、最大轮次、工具失败恢复。

问题：ScriptedLLM 若在断言里检查「最后一次 prompt 含历史」，必须把 `complete` 收到的 messages 存下来。  
解决：`ScriptedLLM.calls` 记录每次请求。

## 6. 真实 LLM 联调

Prompt：

> 用 OpenAI SDK，但 base_url / model / api_key 全从环境变量读，好换 DeepSeek。

问题：没装 `openai` 或 key 为空时，单测不应失败。  
解决：默认测试走 ScriptedLLM；`@pytest.mark.live` + skipif 无 key。

问题：温度过高会导致不输出 JSON。  
解决：`temperature=0.2`，system 里写死「只输出一个 JSON 对象」。

## 7. 异常与 trace

> 工具失败不要中断整个 chat；要有执行日志。

解决：`ToolRegistry.execute` catch 后返回 `ToolResult(ok=False)`；`TraceLogger` 按 session 追加 JSONL，event 包括 `user_input` / `llm_output` / `tool_result` / `error`。

## 8. 仍可改进（题目范围外）

- 没有做递归摘要 LLM、没有向量召回。
- 没有并行 function calling 的原生 API，多工具是模型一次 JSON 里列出多个 call，本进程顺序执行。
- Web UI 仅用于双窗口演示，不是产品前端。
