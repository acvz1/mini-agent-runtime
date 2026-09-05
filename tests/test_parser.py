from mini_agent.parser import parse_agent_output


def test_parse_json_tool_call():
    text = """
    {
      "think": "需要先查天气",
      "tool_calls": [{"name": "weather", "arguments": {"city": "北京"}}],
      "answer": null
    }
    """
    parsed = parse_agent_output(text)
    assert parsed.think == "需要先查天气"
    assert parsed.answer is None
    assert parsed.tool_calls[0].name == "weather"
    assert parsed.tool_calls[0].arguments["city"] == "北京"


def test_parse_fenced_json_final_answer():
    text = """好的，我直接回答。
```json
{"think": "用户只要寒暄", "tool_calls": [], "answer": "你好，我是最小 Agent。"}
```
"""
    parsed = parse_agent_output(text)
    assert parsed.tool_calls == []
    assert parsed.answer == "你好，我是最小 Agent。"


def test_parse_plain_text_as_final_answer():
    parsed = parse_agent_output("今天下午三点开会。")
    assert parsed.tool_calls == []
    assert parsed.answer == "今天下午三点开会。"


def test_parse_multiple_tool_calls():
    text = """{
      "think": "并行记下待办并查天气",
      "tool_calls": [
        {"name": "todo", "arguments": {"action": "add", "item": "买牛奶"}},
        {"name": "weather", "arguments": {"city": "上海"}}
      ],
      "answer": null
    }"""
    parsed = parse_agent_output(text)
    assert [c.name for c in parsed.tool_calls] == ["todo", "weather"]
