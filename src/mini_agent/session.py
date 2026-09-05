from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class Session:
    user_id: str
    session_id: str
    messages: list[dict[str, Any]] = field(default_factory=list)
    todos: list[str] = field(default_factory=list)
    completed_todos: list[str] = field(default_factory=list)
    summary: str = ""
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)

    def touch(self) -> None:
        self.updated_at = _now()

    def to_dict(self) -> dict[str, Any]:
        return {
            "user_id": self.user_id,
            "session_id": self.session_id,
            "messages": self.messages,
            "todos": self.todos,
            "completed_todos": self.completed_todos,
            "summary": self.summary,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Session":
        return cls(
            user_id=data["user_id"],
            session_id=data["session_id"],
            messages=list(data.get("messages") or []),
            todos=list(data.get("todos") or []),
            completed_todos=list(data.get("completed_todos") or []),
            summary=str(data.get("summary") or ""),
            created_at=str(data.get("created_at") or _now()),
            updated_at=str(data.get("updated_at") or _now()),
        )


class FileSessionStore:
    """Disk-backed sessions keyed by (user_id, session_id)."""

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, user_id: str, session_id: str) -> Path:
        safe_user = _safe(user_id)
        safe_sid = _safe(session_id)
        directory = self.root / safe_user
        directory.mkdir(parents=True, exist_ok=True)
        return directory / f"{safe_sid}.json"

    def get_or_create(self, user_id: str, session_id: str) -> Session:
        path = self._path(user_id, session_id)
        if not path.exists():
            return Session(user_id=user_id, session_id=session_id)
        data = json.loads(path.read_text(encoding="utf-8"))
        return Session.from_dict(data)

    def save(self, session: Session) -> None:
        session.touch()
        path = self._path(session.user_id, session.session_id)
        path.write_text(json.dumps(session.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")


def _safe(value: str) -> str:
    return "".join(ch if ch.isalnum() or ch in "-_." else "_" for ch in value) or "default"
