from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from mini_agent.cli import build_runtime
from mini_agent.errors import AgentError
from mini_agent.runtime import result_to_dict

load_dotenv()

app = FastAPI(title="Mini Agent Runtime")
_runtime = None


def get_runtime():
    global _runtime
    if _runtime is None:
        _runtime = build_runtime(os.getenv("DATA_DIR") or "./data")
    return _runtime


class ChatRequest(BaseModel):
    user_id: str = Field(default="A")
    session_id: str = Field(default="window1")
    text: str


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return Path(__file__).with_name("static_index.html").read_text(encoding="utf-8")


@app.post("/api/chat")
def chat(req: ChatRequest):
    if not req.text.strip():
        raise HTTPException(400, "text 不能为空")
    try:
        result = get_runtime().chat(req.user_id, req.session_id, req.text.strip())
    except AgentError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return result_to_dict(result)


@app.get("/api/session/{user_id}/{session_id}")
def session_state(user_id: str, session_id: str):
    runtime = get_runtime()
    session = runtime.store.get_or_create(user_id, session_id)
    return {
        "user_id": session.user_id,
        "session_id": session.session_id,
        "todos": session.todos,
        "completed_todos": session.completed_todos,
        "message_count": len(session.messages),
        "summary": session.summary,
    }
