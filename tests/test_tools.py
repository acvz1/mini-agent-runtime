import pytest

from mini_agent.session import Session
from mini_agent.tools.builtin import builtin_tools
from mini_agent.tools.registry import ToolRegistry, UnknownToolError


@pytest.fixture
def registry() -> ToolRegistry:
    return ToolRegistry(builtin_tools())


def test_registry_exposes_name_description_and_schema(registry: ToolRegistry):
    schemas = {s["name"]: s for s in registry.schemas()}
    assert set(schemas) >= {"calculator", "search", "weather", "todo"}
    for schema in schemas.values():
        assert schema["description"]
        assert schema["parameters"]["type"] == "object"


def test_calculator_evaluates_expression(registry: ToolRegistry):
    session = Session(user_id="a", session_id="s1")
    result = registry.execute("calculator", {"expression": "(2 + 3) * 4"}, session)
    assert result.ok
    assert result.output == "20"


def test_calculator_rejects_unsafe_expression(registry: ToolRegistry):
    session = Session(user_id="a", session_id="s1")
    result = registry.execute("calculator", {"expression": "__import__('os').system('echo x')"}, session)
    assert not result.ok
    assert "不安全" in result.output or "无效" in result.output


def test_search_is_mockable_corpus(registry: ToolRegistry):
    session = Session(user_id="a", session_id="s1")
    result = registry.execute("search", {"query": "Agent Runtime 循环"}, session)
    assert result.ok
    assert "工具" in result.output or "loop" in result.output.lower() or "循环" in result.output


def test_weather_returns_city_forecast(registry: ToolRegistry):
    session = Session(user_id="a", session_id="s1")
    result = registry.execute("weather", {"city": "北京"}, session)
    assert result.ok
    assert "北京" in result.output


def test_todo_is_session_scoped(registry: ToolRegistry):
    s1 = Session(user_id="a", session_id="window1")
    s2 = Session(user_id="a", session_id="window2")
    registry.execute("todo", {"action": "add", "item": "查天气后买伞"}, s1)
    registry.execute("todo", {"action": "add", "item": "写周报"}, s2)
    listed1 = registry.execute("todo", {"action": "list"}, s1)
    listed2 = registry.execute("todo", {"action": "list"}, s2)
    assert "买伞" in listed1.output
    assert "周报" not in listed1.output
    assert "周报" in listed2.output
    assert "买伞" not in listed2.output


def test_unknown_tool_raises(registry: ToolRegistry):
    session = Session(user_id="a", session_id="s1")
    with pytest.raises(UnknownToolError):
        registry.execute("not_a_tool", {}, session)
