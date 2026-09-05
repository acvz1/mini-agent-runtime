from __future__ import annotations

import os

import pytest

from mini_agent.cli import build_runtime

pytestmark = pytest.mark.live


def _has_usable_llm_key() -> bool:
    if os.getenv("LIVE_LLM", "").lower() in {"1", "true", "yes"}:
        return True
    key = os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY") or ""
    if key in {"", "1", "sk-your-key", "changeme"}:
        return False
    return len(key) >= 20


@pytest.mark.skipif(not _has_usable_llm_key(), reason="no real LLM key (set LIVE_LLM=1 and a valid LLM_API_KEY)")
def test_live_tool_and_followup(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    runtime = build_runtime(str(tmp_path))

    first = runtime.chat("A", "window1", "查询北京天气，并记一个待办：出门带伞。最后用中文简短确认。")
    assert first.answer
    assert any(t["name"] == "weather" for t in first.tool_trace)
    assert any(t["name"] == "todo" for t in first.tool_trace)

    follow = runtime.chat("A", "window1", "我刚才记的待办是什么？不要编造其他窗口的内容。")
    assert "伞" in follow.answer or "待办" in follow.answer

    other = runtime.chat("A", "window2", "记一个待办：写周报。不要提带伞。")
    assert "周报" in other.answer
    window1 = runtime.store.get_or_create("A", "window1")
    window2 = runtime.store.get_or_create("A", "window2")
    assert any("伞" in t for t in window1.todos + window1.completed_todos)
    assert any("周报" in t for t in window2.todos + window2.completed_todos)
    assert not any("周报" in t for t in window1.todos)
    assert not any("伞" in t for t in window2.todos)
