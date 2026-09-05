from __future__ import annotations

import argparse
import os
from pathlib import Path

from dotenv import load_dotenv

from mini_agent.errors import AgentError
from mini_agent.llm import OpenAICompatibleLLM
from mini_agent.runtime import AgentRuntime, pretty_trace, result_to_dict
from mini_agent.session import FileSessionStore
from mini_agent.tools.builtin import builtin_tools
from mini_agent.tools.registry import ToolRegistry
from mini_agent.tracing import TraceLogger


def build_runtime(data_dir: str | None = None) -> AgentRuntime:
    load_dotenv()
    root = Path(data_dir or os.getenv("DATA_DIR") or "./data")
    max_turns = int(os.getenv("MAX_LOOP_TURNS") or "8")
    budget = int(os.getenv("CONTEXT_CHAR_BUDGET") or "12000")
    return AgentRuntime(
        llm=OpenAICompatibleLLM(),
        registry=ToolRegistry(builtin_tools()),
        store=FileSessionStore(root / "sessions"),
        tracer=TraceLogger(root / "traces"),
        max_loop_turns=max_turns,
        context_char_budget=budget,
        data_dir=root,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Minimal Agent Runtime CLI")
    parser.add_argument("--user", default="A", help="user id")
    parser.add_argument("--session", default="window1", help="session / window id")
    parser.add_argument("--data-dir", default=None)
    parser.add_argument("text", nargs="*", help="optional one-shot question")
    args = parser.parse_args()

    runtime = build_runtime(args.data_dir)
    if args.text:
        _run_once(runtime, args.user, args.session, " ".join(args.text))
        return

    print(f"mini-agent  user={args.user}  session={args.session}")
    print("输入消息后回车。Ctrl+C 退出。\n")
    while True:
        try:
            text = input("you> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return
        if not text:
            continue
        if text in {"/exit", "/quit"}:
            return
        _run_once(runtime, args.user, args.session, text)


def _run_once(runtime: AgentRuntime, user: str, session: str, text: str) -> None:
    try:
        result = runtime.chat(user, session, text)
    except AgentError as exc:
        print(f"error> {exc}")
        return
    print(f"think> {result.think}")
    print("trace>")
    print(pretty_trace(result.tool_trace))
    print(f"agent> {result.answer}\n")
    _ = result_to_dict(result)


if __name__ == "__main__":
    main()
