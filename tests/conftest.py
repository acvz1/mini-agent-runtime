from __future__ import annotations

from pathlib import Path

import pytest

from mini_agent.runtime import AgentRuntime
from mini_agent.session import FileSessionStore
from mini_agent.tools.builtin import builtin_tools
from mini_agent.tools.registry import ToolRegistry
from mini_agent.tracing import TraceLogger


@pytest.fixture
def tmp_store(tmp_path: Path) -> FileSessionStore:
    return FileSessionStore(tmp_path / "sessions")


@pytest.fixture
def registry() -> ToolRegistry:
    return ToolRegistry(builtin_tools())


class ScriptedLLM:
    """Deterministic LLM for tests: return pre-scripted strings in order."""

    def __init__(self, replies: list[str]) -> None:
        self.replies = list(replies)
        self.calls: list[list[dict]] = []

    def complete(self, messages: list[dict]) -> str:
        self.calls.append(messages)
        if not self.replies:
            raise AssertionError("ScriptedLLM has no remaining replies")
        return self.replies.pop(0)


@pytest.fixture
def make_runtime(tmp_store, registry, tmp_path):
    def _make(replies: list[str], **kwargs) -> tuple[AgentRuntime, ScriptedLLM]:
        llm = ScriptedLLM(replies)
        runtime = AgentRuntime(
            llm=llm,
            registry=registry,
            store=tmp_store,
            tracer=TraceLogger(tmp_path / "traces"),
            max_loop_turns=kwargs.get("max_loop_turns", 8),
            context_char_budget=kwargs.get("context_char_budget", 12000),
            data_dir=tmp_path,
        )
        return runtime, llm

    return _make
