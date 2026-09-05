from mini_agent.errors import MaxTurnsExceeded


def test_direct_reply_without_tools(make_runtime):
    runtime, _ = make_runtime(
        [
            '{"think": "寒暄即可", "tool_calls": [], "answer": "你好，有什么需要帮忙的？"}',
        ]
    )
    result = runtime.chat("A", "w1", "你好")
    assert result.answer == "你好，有什么需要帮忙的？"
    assert result.tool_trace == []


def test_tool_then_final_answer(make_runtime):
    runtime, _ = make_runtime(
        [
            '{"think": "先算一下", "tool_calls": [{"name": "calculator", "arguments": {"expression": "12*8"}}], "answer": null}',
            '{"think": "有结果了", "tool_calls": [], "answer": "12 乘 8 等于 96。"}',
        ]
    )
    result = runtime.chat("A", "w1", "12*8 等于多少")
    assert "96" in result.answer
    assert result.tool_trace[0]["name"] == "calculator"
    assert result.tool_trace[0]["ok"] is True


def test_continue_loop_with_two_tools(make_runtime):
    runtime, _ = make_runtime(
        [
            '{"think": "查天气", "tool_calls": [{"name": "weather", "arguments": {"city": "北京"}}], "answer": null}',
            '{"think": "记下待办", "tool_calls": [{"name": "todo", "arguments": {"action": "add", "item": "出门带伞"}}], "answer": null}',
            '{"think": "结束", "tool_calls": [], "answer": "北京可能需要伞，已记下出门带伞。"}',
        ]
    )
    result = runtime.chat("A", "window1", "查北京天气并记一个待办出门带伞")
    assert "带伞" in result.answer
    assert [t["name"] for t in result.tool_trace] == ["weather", "todo"]


def test_two_windows_do_not_share_todos(make_runtime, tmp_store):
    runtime, _ = make_runtime(
        [
            '{"think": "记待办", "tool_calls": [{"name": "todo", "arguments": {"action": "add", "item": "查天气后买伞"}}], "answer": null}',
            '{"think": "好了", "tool_calls": [], "answer": "已记下查天气后买伞。"}',
            '{"think": "记周报", "tool_calls": [{"name": "todo", "arguments": {"action": "add", "item": "写周报"}}], "answer": null}',
            '{"think": "好了", "tool_calls": [], "answer": "已记下写周报。"}',
            '{"think": "列待办", "tool_calls": [{"name": "todo", "arguments": {"action": "list"}}], "answer": null}',
            '{"think": "窗口1只有买伞", "tool_calls": [], "answer": "当前待办：查天气后买伞"}',
        ]
    )
    runtime.chat("A", "window1", "记待办：查天气后买伞")
    runtime.chat("A", "window2", "记待办：写周报")
    result = runtime.chat("A", "window1", "我刚才记了哪些待办？")
    assert "买伞" in result.answer
    assert "周报" not in result.answer
    w1 = tmp_store.get_or_create("A", "window1")
    w2 = tmp_store.get_or_create("A", "window2")
    assert w1.todos != w2.todos


def test_pure_dialogue_followup_uses_history(make_runtime):
    runtime, llm = make_runtime(
        [
            '{"think": "记住名字", "tool_calls": [], "answer": "好的，小明。"}',
            '{"think": "从历史取名字", "tool_calls": [], "answer": "你叫小明。"}',
        ]
    )
    runtime.chat("A", "w1", "我叫小明")
    result = runtime.chat("A", "w1", "我叫什么？")
    assert "小明" in result.answer
    last_prompt = "\n".join(m.get("content", "") for m in llm.calls[-1])
    assert "我叫小明" in last_prompt
    assert "我叫什么？" in last_prompt


def test_tool_followup_sees_previous_tool_state(make_runtime):
    runtime, llm = make_runtime(
        [
            '{"think": "添加", "tool_calls": [{"name": "todo", "arguments": {"action": "add", "item": "写周报"}}], "answer": null}',
            '{"think": "已添加", "tool_calls": [], "answer": "已添加写周报。"}',
            '{"think": "完成它", "tool_calls": [{"name": "todo", "arguments": {"action": "complete", "item": "写周报"}}], "answer": null}',
            '{"think": "完成", "tool_calls": [], "answer": "写周报已完成。"}',
        ]
    )
    runtime.chat("A", "w2", "记一个待办：写周报")
    result = runtime.chat("A", "w2", "把刚才那个待办标成完成")
    assert "完成" in result.answer
    last_prompt = "\n".join(m.get("content", "") for m in llm.calls[-1])
    assert "写周报" in last_prompt


def test_max_turns_stops_the_loop(make_runtime):
    runtime, _ = make_runtime(
        [
            '{"think": "再算", "tool_calls": [{"name": "calculator", "arguments": {"expression": "1+1"}}], "answer": null}',
            '{"think": "再算", "tool_calls": [{"name": "calculator", "arguments": {"expression": "1+1"}}], "answer": null}',
            '{"think": "再算", "tool_calls": [{"name": "calculator", "arguments": {"expression": "1+1"}}], "answer": null}',
        ],
        max_loop_turns=2,
    )
    try:
        runtime.chat("A", "w1", "一直算 1+1")
        raised = False
    except MaxTurnsExceeded:
        raised = True
    assert raised


def test_tool_error_is_fed_back_and_agent_can_recover(make_runtime):
    runtime, _ = make_runtime(
        [
            '{"think": "错表达式", "tool_calls": [{"name": "calculator", "arguments": {"expression": "???"}}], "answer": null}',
            '{"think": "改用合法表达式", "tool_calls": [{"name": "calculator", "arguments": {"expression": "2+2"}}], "answer": null}',
            '{"think": "好了", "tool_calls": [], "answer": "结果是 4。"}',
        ]
    )
    result = runtime.chat("A", "w1", "帮我算一下")
    assert result.answer == "结果是 4。"
    assert result.tool_trace[0]["ok"] is False
    assert result.tool_trace[1]["ok"] is True
