from __future__ import annotations

import json
from typing import Any

from mini_agent.session import Session

SYSTEM_PROMPT = """你是一个最小可用 Agent Runtime。你可以选择直接回答，或调用工具后再回答。

输出必须是单个 JSON 对象，不要输出 JSON 以外的说明。字段：
- think: 简短思考过程（给运行时日志用，也便于后续追问）
- tool_calls: 数组。需要工具时填写；不需要则为 []
- answer: 给用户的最终答复。只要还要调用工具，answer 必须为 null

工具调用格式：
{{"think": "...", "tool_calls": [{{"name": "weather", "arguments": {{"city": "北京"}}}}], "answer": null}}

最终回答格式：
{{"think": "...", "tool_calls": [], "answer": "..."}}

规则：
1. 只使用下列已注册工具，参数必须符合 schema。
2. 工具结果出现后，再决定继续调用还是给出 answer。
3. 当前窗口的待办与对话是独立 session，不要引用其他窗口。
4. 用户追问时，优先使用对话历史、工具结果和待办快照。
5. 计算题必须用 calculator；天气用 weather；检索资料用 search；待办用 todo。

已注册工具:
{tool_schemas}

当前 session 状态快照:
- user_id: {user_id}
- session_id: {session_id}
- open_todos: {todos}
- completed_todos: {completed}
"""


class ContextManager:
    """Pack session state into LLM messages, with cheap truncation/summary."""

    def __init__(self, char_budget: int = 12_000, keep_recent_messages: int = 8) -> None:
        self.char_budget = char_budget
        self.keep_recent_messages = keep_recent_messages

    def build(self, session: Session, tool_schemas: list[dict[str, Any]]) -> list[dict[str, str]]:
        system = SYSTEM_PROMPT.format(
            tool_schemas=json.dumps(tool_schemas, ensure_ascii=False, indent=2),
            user_id=session.user_id,
            session_id=session.session_id,
            todos=session.todos or "[]",
            completed=session.completed_todos or "[]",
        )
        history = list(session.messages)
        recent = history[-self.keep_recent_messages :]
        older = history[: -self.keep_recent_messages] if len(history) > self.keep_recent_messages else []

        packed_older = self._pack_older(session, older)
        messages: list[dict[str, str]] = [{"role": "system", "content": system}]
        if packed_older:
            messages.append({"role": "system", "content": packed_older})
        messages.extend(self._render(recent))

        if self._chars(messages) <= self.char_budget:
            return messages

        # Second-pass: shrink think fields in recent assistant messages, then drop oldest.
        messages = [{"role": "system", "content": system}]
        if packed_older:
            messages.append({"role": "system", "content": packed_older})
        messages.extend(self._render(recent, truncate_think=True))
        while len(messages) > 2 and self._chars(messages) > self.char_budget:
            # keep system + last user/tool/assistant
            messages.pop(2 if messages[1]["role"] == "system" and messages[1] is not messages[0] else 1)
            if messages[0]["role"] != "system":
                break
        return messages

    def _pack_older(self, session: Session, older: list[dict[str, Any]]) -> str:
        if not older and not session.summary:
            return ""
        snippets: list[str] = []
        if session.summary:
            snippets.append(session.summary)
        for msg in older:
            role = msg.get("role", "")
            content = str(msg.get("content") or "")
            if role == "user":
                snippets.append(f"用户: {content[:80]}")
            elif role == "tool":
                snippets.append(f"工具{msg.get('name', '')}: {content[:80]}")
            elif role == "assistant":
                snippets.append(f"助手: {content[:80]}")
        joined = "；".join(snippets)
        if len(joined) > max(400, self.char_budget // 4):
            joined = joined[: self.char_budget // 4] + "…"
        session.summary = joined[:1500]
        return "此前对话摘要（旧轮次已压缩，细节可能丢失）:\n" + joined

    def _render(self, messages: list[dict[str, Any]], truncate_think: bool = False) -> list[dict[str, str]]:
        rendered: list[dict[str, str]] = []
        for msg in messages:
            role = msg.get("role") or "user"
            content = str(msg.get("content") or "")
            if role == "tool":
                name = msg.get("name") or "tool"
                rendered.append({"role": "user", "content": f"[工具结果 {name}]\n{content}"})
                continue
            if role == "assistant" and truncate_think:
                content = _truncate_think(content)
            mapped = "assistant" if role == "assistant" else "user"
            rendered.append({"role": mapped, "content": content})
        return rendered

    def _chars(self, messages: list[dict[str, str]]) -> int:
        return sum(len(m.get("content") or "") for m in messages)


def _truncate_think(content: str, limit: int = 180) -> str:
    try:
        obj = json.loads(content)
    except json.JSONDecodeError:
        return content[:400]
    think = str(obj.get("think") or "")
    if len(think) > limit:
        obj["think"] = think[:limit] + "…"
    return json.dumps(obj, ensure_ascii=False)
