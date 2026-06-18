from __future__ import annotations

from tools.base import BaseTool


class TodoTool(BaseTool):
    name = "todo"
    description = "Create, list, and update tasks in the current session memory."

    def run(self, args: dict, session: dict | None = None) -> dict:
        operation = args.get("operation")
        memory, session_id = self._get_context(session)
        if not memory or not session_id:
            return {"ok": False, "error": "todo requires session context"}

        if operation == "create":
            title = args.get("title")
            if not isinstance(title, str) or not title.strip():
                return {"ok": False, "error": "title is required"}
            task = memory.upsert_task(
                session_id,
                {
                    "title": title.strip(),
                    "status": args.get("status", "in_progress"),
                    "notes": args.get("notes", ""),
                },
            )
            return {"ok": True, "task": task}

        if operation == "list":
            return {"ok": True, "tasks": memory.load_session(session_id)["tasks"]}

        if operation == "update":
            task_id = args.get("task_id")
            if not isinstance(task_id, str) or not task_id.strip():
                return {"ok": False, "error": "task_id is required"}

            existing_tasks = memory.load_session(session_id)["tasks"]
            existing = next((task for task in existing_tasks if task.get("task_id") == task_id), None)
            if not existing:
                return {"ok": False, "error": f"task not found: {task_id}"}

            updated = {
                **existing,
                "status": args.get("status", existing.get("status", "in_progress")),
                "notes": args.get("notes", existing.get("notes", "")),
                "title": args.get("title", existing.get("title", "")),
            }
            task = memory.upsert_task(session_id, updated)
            return {"ok": True, "task": task}

        return {"ok": False, "error": "operation must be create, list, or update"}

    @staticmethod
    def _get_context(session: dict | None):
        if not session:
            return None, None
        return session.get("memory"), session.get("session_id")

