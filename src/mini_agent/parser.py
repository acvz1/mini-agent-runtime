from __future__ import annotations

import json
import re
from typing import Any

from mini_agent.types import ParsedAgentOutput, ToolCall

_FENCE_RE = re.compile(r"```(?:json)?\s*([\s\S]*?)```", re.IGNORECASE)


def parse_agent_output(text: str) -> ParsedAgentOutput:
    """Extract think / tool_calls / final answer from an LLM completion.

    Primary protocol is JSON. Markdown fences are accepted. If no JSON object
    is found, the raw text is treated as a final user-facing answer.
    """
    raw = (text or "").strip()
    if not raw:
        return ParsedAgentOutput(think="", tool_calls=[], answer="")

    obj = _extract_json_object(raw)
    if obj is None:
        return ParsedAgentOutput(think="", tool_calls=[], answer=raw)

    think = str(obj.get("think") or obj.get("thought") or "").strip()
    answer = obj.get("answer")
    if answer is not None:
        answer = str(answer).strip() or None

    calls: list[ToolCall] = []
    raw_calls = obj.get("tool_calls") or obj.get("tools") or []
    if isinstance(raw_calls, dict):
        raw_calls = [raw_calls]
    if isinstance(raw_calls, list):
        for item in raw_calls:
            if not isinstance(item, dict):
                continue
            name = str(item.get("name") or item.get("tool") or "").strip()
            if not name:
                continue
            arguments = item.get("arguments") or item.get("args") or {}
            if isinstance(arguments, str):
                try:
                    arguments = json.loads(arguments)
                except json.JSONDecodeError:
                    arguments = {"_raw": arguments}
            if not isinstance(arguments, dict):
                arguments = {"value": arguments}
            calls.append(ToolCall(name=name, arguments=arguments))

    if calls:
        return ParsedAgentOutput(think=think, tool_calls=calls, answer=None)
    return ParsedAgentOutput(think=think, tool_calls=[], answer=answer or raw)


def _extract_json_object(text: str) -> dict[str, Any] | None:
    candidates: list[str] = []
    for match in _FENCE_RE.finditer(text):
        candidates.append(match.group(1).strip())
    candidates.append(text)

    for candidate in candidates:
        parsed = _try_load_json(candidate)
        if parsed is not None:
            return parsed
        start = candidate.find("{")
        end = candidate.rfind("}")
        if start >= 0 and end > start:
            parsed = _try_load_json(candidate[start : end + 1])
            if parsed is not None:
                return parsed
    return None


def _try_load_json(text: str) -> dict[str, Any] | None:
    try:
        value = json.loads(text)
    except json.JSONDecodeError:
        return None
    return value if isinstance(value, dict) else None
