from mini_agent.tools.calculator import CalculatorTool
from mini_agent.tools.search import SearchTool
from mini_agent.tools.todo import TodoTool
from mini_agent.tools.weather import WeatherTool


def builtin_tools():
    return [CalculatorTool(), SearchTool(), WeatherTool(), TodoTool()]
