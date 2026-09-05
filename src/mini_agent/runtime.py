from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from mini_agent.context import ContextManager
from mini_agent.errors import MaxTurnsExceeded, UnknownToolError
from mini_agent.parser import parse_agent_output
from mini_agent.session import FileSessionStore, Session
from mini_agent.tools.builtin import builtin_tools
from mini_agent.tools.registry import ToolRegistry
from mini_agent.tracing import TraceLogger
from mini_agent.types import AgentResult, ToolResult


class AgentRuntime:
    def __init__(
        self,
        llm,
        registry: ToolRegistry | None = None,
        store: FileSessionStore | None = None,
        tracer: TraceLogger | None = None,
        max_loop_turns: int = 8,
        context_char_budget: int = 12_000,
        data_dir: str | Path | None = None,
    ) -> None:
        data_root = Path(data_dir or "./data")
        self.llm = llm
        self.registry = registry or ToolRegistry(builtin_tools())
        self.store = store or FileSessionStore(data_root / "sessions")
        self.tracer = tracer or TraceLogger(data_root / "traces")
        self.max_loop_turns = max_loop_turns
        self.context = ContextManager(char_budget=context_char_budget)

    def chat(self, user_id: str, session_id: str, user_text: str) -> AgentResult:
        session = self.store.get_or_create(user_id, session_id)
        session.messages.append({"role": "user", "content": user_text})
        self.tracer.log(user_id, session_id, "user_input", {"text": user_text})

        trace: list[dict[str, Any]] = []
        last_think = ""
        try:
            for turn in range(1, self.max_loop_turns + 1):
                messages = self.context.build(session, self.registry.schemas())
                raw = self.llm.complete(messages)
                parsed = parse_agent_output(raw)
                last_think = parsed.think
                session.messages.append({"role": "assistant", "content": raw})
                self.tracer.log(
                    user_id,
                    session_id,
                    "llm_output",
                    {
                        "turn": turn,
                        "think": parsed.think,
                        "tool_calls": [c.__dict__ for c in parsed.tool_calls],
                        "has_answer": parsed.answer is not None,
                        "raw": raw[:4000],
                    },
                )

                if parsed.tool_calls:
                    for call in parsed.tool_calls:
                        result = self._run_tool(call.name, call.arguments, session)
                        trace.append(_trace_item(result, turn))
                        session.messages.append(
                            {
                                "role": "tool",
                                "name": result.name,
                                "content": result.output,
                                "ok": result.ok,
                            }
                        )
                        self.tracer.log(
                            user_id,
                            session_id,
                            "tool_result",
                            {
                                "turn": turn,
                                "name": result.name,
                                "arguments": result.arguments,
                                "ok": result.ok,
                                "output": result.output,
                            },
                        )
                    self.store.save(session)
                    continue

                answer = parsed.answer or "（模型没有给出 answer）"
                self.store.save(session)
                return AgentResult(
                    answer=answer,
                    think=last_think,
                    tool_trace=trace,
                    session_id=session_id,
                    user_id=user_id,
                    turns_used=turn,
                )

            self.store.save(session)
            raise MaxTurnsExceeded(f"超过最大循环轮次 {self.max_loop_turns}，仍未给出最终回答")
        except MaxTurnsExceeded:
            self.tracer.log(user_id, session_id, "error", {"type": "MaxTurnsExceeded"})
            raise
        except Exception as exc:
            self.tracer.log(user_id, session_id, "error", {"type": type(exc).__name__, "message": str(exc)})
            self.store.save(session)
            raise

    def _run_tool(self, name: str, arguments: dict[str, Any], session: Session) -> ToolResult:
        try:
            return self.registry.execute(name, arguments, session)
        except UnknownToolError as exc:
            return ToolResult(
                name=name,
                arguments=arguments,
                output=str(exc),
                ok=False,
                error_type="UnknownToolError",
            )


def _trace_item(result: ToolResult, turn: int) -> dict[str, Any]:
    return {
        "turn": turn,
        "name": result.name,
        "arguments": result.arguments,
        "ok": result.ok,
        "output": result.output,
        "error_type": result.error_type,
    }


def result_to_dict(result: AgentResult) -> dict[str, Any]:
    return {
        "answer": result.answer,
        "think": result.think,
        "tool_trace": result.tool_trace,
        "user_id": result.user_id,
        "session_id": result.session_id,
        "turns_used": result.turns_used,
    }


def pretty_trace(trace: list[dict[str, Any]]) -> str:
    if not trace:
        return "(no tools)"
    lines = []
    for item in trace:
        status = "ok" if item.get("ok") else "error"
        lines.append(
            f"  [{item.get('turn')}] {item.get('name')} {json.dumps(item.get('arguments'), ensure_ascii=False)} -> {status}: {item.get('output')}"
        )
    return "\n".join(lines)
