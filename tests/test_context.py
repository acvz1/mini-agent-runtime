from mini_agent.context import ContextManager
from mini_agent.session import Session


def test_context_includes_user_tool_result_and_truncated_think():
    session = Session(user_id="A", session_id="w1")
    session.messages = [
        {"role": "user", "content": "北京天气？"},
        {
            "role": "assistant",
            "content": '{"think": "先调用天气工具", "tool_calls": [{"name": "weather", "arguments": {"city": "北京"}}]}',
        },
        {"role": "tool", "name": "weather", "content": "北京 晴 26°C"},
        {"role": "assistant", "content": '{"think": "可以回答了", "answer": "北京晴，26度"}'},
    ]
    mgr = ContextManager(char_budget=20_000)
    messages = mgr.build(session, tool_schemas=[{"name": "weather", "description": "查天气", "parameters": {}}])
    joined = "\n".join(m["content"] for m in messages if m.get("content"))
    assert "北京天气？" in joined
    assert "北京 晴 26°C" in joined
    assert "weather" in joined
    assert "think" in joined.lower() or "思考" in joined


def test_context_compresses_old_turns_but_keeps_recent_and_todos():
    session = Session(user_id="A", session_id="w1")
    session.todos = ["写周报"]
    for i in range(30):
        session.messages.append({"role": "user", "content": f"旧消息-{i}-" + ("x" * 200)})
        session.messages.append({"role": "assistant", "content": f"旧回复-{i}-" + ("y" * 200)})
    session.messages.append({"role": "user", "content": "刚才周报待办还在吗？"})
    mgr = ContextManager(char_budget=2500)
    messages = mgr.build(session, tool_schemas=[])
    joined = "\n".join(m["content"] for m in messages if m.get("content"))
    assert "刚才周报待办还在吗？" in joined
    assert "写周报" in joined
    assert "摘要" in joined or "summary" in joined.lower()
    assert len(joined) < 8000
    assert "旧消息-0-" not in joined or "摘要" in joined
