from __future__ import annotations

from typing import Any

from mini_agent.session import Session


class TodoTool:
    name = "todo"
    description = (
        "管理当前 session 的待办。action=add 添加，list 查看，complete 完成。"
        "待办只存在于当前窗口，不会泄漏到同一用户的其他窗口。"
    )
    parameters = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["add", "list", "complete"],
                "description": "操作类型",
            },
            "item": {"type": "string", "description": "待办内容。add/complete 时必填"},
        },
        "required": ["action"],
    }

    def execute(self, arguments: dict[str, Any], session: Session) -> str:
        action = str(arguments.get("action") or "").strip().lower()
        item = str(arguments.get("item") or "").strip()
        if action == "add":
            if not item:
                raise ValueError("add 需要 item")
            if item not in session.todos:
                session.todos.append(item)
            return f"已添加待办: {item}。当前待办: {session.todos}"
        if action == "list":
            return f"当前待办: {session.todos or '（空）'}；已完成: {session.completed_todos or '（空）'}"
        if action == "complete":
            if not item:
                raise ValueError("complete 需要 item")
            matched = _match_item(item, session.todos)
            if matched is None:
                return f"未找到待办「{item}」。当前待办: {session.todos}"
            session.todos.remove(matched)
            session.completed_todos.append(matched)
            return f"已完成待办: {matched}。剩余待办: {session.todos or '（空）'}"
        raise ValueError("action 必须是 add / list / complete")


def _match_item(item: str, todos: list[str]) -> str | None:
    if item in todos:
        return item
    for todo in todos:
        if item in todo or todo in item:
            return todo
    return None
