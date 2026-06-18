from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4


class TraceLogger:
    """Collects one run_turn execution trace and writes it as JSON."""

    def __init__(self, session_id: str, user_input: str, trace_dir: str | Path = "data/traces"):
        self.session_id = session_id
        self.user_input = user_input
        self.trace_dir = Path(trace_dir)
        self.trace_dir.mkdir(parents=True, exist_ok=True)
        self.created_at = datetime.now(timezone.utc).isoformat()
        self.trace_id = f"trace_{uuid4().hex[:12]}"
        self.steps: list[dict] = []
        self.final_answer: str | None = None
        self.fallback_answer: str | None = None
        self.error: str | None = None

    def add_step(self, step: dict) -> None:
        self.steps.append(step)

    def set_final_answer(self, answer: str) -> None:
        self.final_answer = answer

    def set_fallback_answer(self, answer: str) -> None:
        self.fallback_answer = answer

    def set_error(self, error: str) -> None:
        self.error = error

    def save(self) -> Path:
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        safe_session = self.session_id.replace("/", "_").replace("\\", "_")
        path = self.trace_dir / f"{timestamp}_{safe_session}_{self.trace_id}.json"
        payload = {
            "trace_id": self.trace_id,
            "created_at": self.created_at,
            "session_id": self.session_id,
            "user_input": self.user_input,
            "steps": self.steps,
            "final_answer": self.final_answer,
            "fallback_answer": self.fallback_answer,
            "error": self.error,
        }
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return path
