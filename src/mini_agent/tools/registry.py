from __future__ import annotations

from typing import Any, Protocol

from mini_agent.errors import UnknownToolError
from mini_agent.session import Session
from mini_agent.types import ToolResult


class Tool(Protocol):
    name: str
    description: str
    parameters: dict[str, Any]

    def execute(self, arguments: dict[str, Any], session: Session) -> str: ...


class ToolRegistry:
    def __init__(self, tools: list[Tool] | None = None) -> None:
        self._tools: dict[str, Tool] = {}
        for tool in tools or []:
            self.register(tool)

    def register(self, tool: Tool) -> None:
        self._tools[tool.name] = tool

    def schemas(self) -> list[dict[str, Any]]:
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.parameters,
            }
            for tool in self._tools.values()
        ]

    def execute(self, name: str, arguments: dict[str, Any], session: Session) -> ToolResult:
        tool = self._tools.get(name)
        if tool is None:
            raise UnknownToolError(f"未注册的工具: {name}")
        try:
            output = tool.execute(arguments or {}, session)
            return ToolResult(name=name, arguments=arguments or {}, output=str(output), ok=True)
        except UnknownToolError:
            raise
        except Exception as exc:  # tool failures become observations, not crashes
            return ToolResult(
                name=name,
                arguments=arguments or {},
                output=f"工具执行失败: {exc}",
                ok=False,
                error_type=type(exc).__name__,
            )
