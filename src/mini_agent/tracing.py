from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class TraceLogger:
    """Append-only JSONL traces, not injected into the LLM context."""

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def log(self, user_id: str, session_id: str, event: str, payload: dict[str, Any]) -> None:
        path = self.root / f"{_safe(user_id)}__{_safe(session_id)}.jsonl"
        record = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "event": event,
            "user_id": user_id,
            "session_id": session_id,
            **payload,
        }
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")


def _safe(value: str) -> str:
    return "".join(ch if ch.isalnum() or ch in "-_." else "_" for ch in value) or "default"
