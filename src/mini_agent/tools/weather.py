from __future__ import annotations

from typing import Any

from mini_agent.session import Session

_WEATHER = {
    "北京": "北京 多云转阴，26°C，风力3级，傍晚可能小雨，建议带伞。",
    "上海": "上海 晴，29°C，湿度70%，适合户外，注意防晒。",
    "广州": "广州 阵雨，31°C，体感闷热，外出请带伞。",
    "深圳": "深圳 晴间多云，30°C，东南风。",
    "杭州": "杭州 阴，24°C，空气良好。",
}


class WeatherTool:
    name = "weather"
    description = "查询城市天气（mock 数据）。支持北京/上海/广州/深圳/杭州，其他城市返回默认预报。"
    parameters = {
        "type": "object",
        "properties": {
            "city": {"type": "string", "description": "城市名，例如 北京"},
        },
        "required": ["city"],
    }

    def execute(self, arguments: dict[str, Any], session: Session) -> str:
        city = str(arguments.get("city") or "").strip()
        if not city:
            raise ValueError("缺少 city")
        if city in _WEATHER:
            return _WEATHER[city]
        return f"{city} 晴间多云，25°C（默认 mock 预报）。"
