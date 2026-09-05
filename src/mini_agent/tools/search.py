from __future__ import annotations

from typing import Any

from mini_agent.session import Session

_CORPUS = [
    {
        "title": "Agent Runtime 基本循环",
        "body": "最小 Agent 循环：接收用户输入 -> 判断直接回复或调用工具 -> 执行工具 -> 根据工具结果决定继续 loop 还是返回用户。",
    },
    {
        "title": "Session 隔离",
        "body": "同一用户的不同窗口是独立 session。待办、对话历史、摘要都按 (user_id, session_id) 隔离，互不影响。",
    },
    {
        "title": "Context 压缩",
        "body": "上下文过长时保留最近若干轮原文，旧轮次折叠成摘要。工具 schema、当前待办快照始终放入 system。",
    },
    {
        "title": "周报写法",
        "body": "周报通常包括本周完成、进行中、风险阻塞、下周计划。可用待办列表作为素材。",
    },
]


class SearchTool:
    name = "search"
    description = "在内置知识库中检索（mock 搜索）。适合查 Agent 设计、session、周报等本地资料。"
    parameters = {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "检索关键词"},
        },
        "required": ["query"],
    }

    def execute(self, arguments: dict[str, Any], session: Session) -> str:
        query = str(arguments.get("query") or "").strip()
        if not query:
            raise ValueError("缺少 query")
        tokens = [t.lower() for t in query.replace("，", " ").replace(",", " ").split() if t]
        scored: list[tuple[int, dict[str, str]]] = []
        for doc in _CORPUS:
            hay = (doc["title"] + " " + doc["body"]).lower()
            score = sum(1 for t in tokens if t in hay)
            if score:
                scored.append((score, doc))
        if not scored:
            return f"未找到与「{query}」相关的资料。"
        scored.sort(key=lambda item: item[0], reverse=True)
        lines = [f"- {doc['title']}: {doc['body']}" for _, doc in scored[:3]]
        return "检索结果:\n" + "\n".join(lines)
