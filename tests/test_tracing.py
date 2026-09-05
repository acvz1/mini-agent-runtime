from mini_agent.runtime import AgentRuntime
from mini_agent.tools.builtin import builtin_tools
from mini_agent.tools.registry import ToolRegistry
from mini_agent.tracing import TraceLogger


class _LLM:
    def __init__(self) -> None:
        self.n = 0

    def complete(self, messages):
        self.n += 1
        if self.n == 1:
            return '{"think": "算一下", "tool_calls": [{"name": "calculator", "arguments": {"expression": "1+2"}}], "answer": null}'
        return '{"think": "好了", "tool_calls": [], "answer": "3"}'


def test_trace_logger_writes_jsonl(tmp_path):
    tracer = TraceLogger(tmp_path / "traces")
    runtime = AgentRuntime(
        llm=_LLM(),
        registry=ToolRegistry(builtin_tools()),
        store=None,
        tracer=tracer,
        data_dir=tmp_path,
    )
    runtime.chat("A", "w1", "1+2")
    files = list((tmp_path / "traces").glob("*.jsonl"))
    assert files
    text = files[0].read_text(encoding="utf-8")
    assert "user_input" in text
    assert "tool_result" in text
    assert "calculator" in text
