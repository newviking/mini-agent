from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4


class FileMemoryStore:
    """JSON-file backed session memory."""

    def __init__(self, base_dir: str | Path = "data/sessions"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def load_session(self, session_id: str) -> dict:
        path = self._session_path(session_id)
        if not path.exists():
            return self._new_session(session_id)

        data = json.loads(path.read_text(encoding="utf-8"))
        data.setdefault("session_id", session_id)
        data.setdefault("messages", [])
        data.setdefault("tasks", [])
        return data

    def save_session(self, session: dict) -> None:
        session_id = session.get("session_id")
        if not session_id:
            raise ValueError("session_id is required")
        session.setdefault("messages", [])
        session.setdefault("tasks", [])
        path = self._session_path(session_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(session, ensure_ascii=False, indent=2), encoding="utf-8")

    def append_message(self, session_id: str, role: str, content: str) -> dict:
        session = self.load_session(session_id)
        session["messages"].append({"role": role, "content": content})
        self.save_session(session)
        return session

    def get_recent_messages(self, session_id: str, limit: int = 8) -> list[dict]:
        session = self.load_session(session_id)
        return session["messages"][-limit:]

    def get_active_tasks(self, session_id: str) -> list[dict]:
        session = self.load_session(session_id)
        return [task for task in session["tasks"] if task.get("status") != "done"]

    def upsert_task(self, session_id: str, task: dict) -> dict:
        session = self.load_session(session_id)
        normalized = self._normalize_task(task)
        tasks = session["tasks"]

        for index, existing in enumerate(tasks):
            if existing.get("task_id") == normalized["task_id"]:
                merged = {**existing, **normalized}
                tasks[index] = merged
                self.save_session(session)
                return merged

        tasks.append(normalized)
        self.save_session(session)
        return normalized

    def _normalize_task(self, task: dict) -> dict:
        title = task.get("title", "").strip()
        status = task.get("status", "in_progress")
        if status not in {"in_progress", "done", "blocked"}:
            status = "in_progress"

        return {
            "task_id": task.get("task_id") or f"task_{uuid4().hex[:8]}",
            "title": title,
            "status": status,
            "notes": task.get("notes", ""),
        }

    def _session_path(self, session_id: str) -> Path:
        safe_id = session_id.replace("/", "_").replace("\\", "_")
        return self.base_dir / f"{safe_id}.json"

    @staticmethod
    def _new_session(session_id: str) -> dict:
        return {"session_id": session_id, "messages": [], "tasks": []}

