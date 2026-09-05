from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ToolCall:
    name: str
    arguments: dict[str, Any]


@dataclass
class ParsedAgentOutput:
    think: str
    tool_calls: list[ToolCall]
    answer: str | None


@dataclass
class ToolResult:
    name: str
    arguments: dict[str, Any]
    output: str
    ok: bool
    error_type: str | None = None


@dataclass
class AgentResult:
    answer: str
    think: str = ""
    tool_trace: list[dict[str, Any]] = field(default_factory=list)
    session_id: str = ""
    user_id: str = ""
    turns_used: int = 0
