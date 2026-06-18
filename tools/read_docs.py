from __future__ import annotations

from pathlib import Path

from tools.base import BaseTool


class ReadDocsTool(BaseTool):
    name = "read_docs"
    description = "Read markdown files from the local docs directory."

    def __init__(self, docs_dir: str | Path = "docs"):
        self.docs_dir = Path(docs_dir)

    def run(self, args: dict, session: dict | None = None) -> dict:
        requested = args.get("path") or args.get("file")
        if not isinstance(requested, str) or not requested.strip():
            return {"ok": False, "error": "path is required"}
        if not requested.endswith(".md"):
            return {"ok": False, "error": "only markdown files can be read"}

        base = self.docs_dir.resolve()
        path = (self.docs_dir / requested).resolve()
        try:
            relative = path.relative_to(base)
        except ValueError:
            return {"ok": False, "error": "path traversal is not allowed"}

        if not path.exists() or not path.is_file():
            return {"ok": False, "error": f"document not found: {relative.as_posix()}"}

        return {
            "ok": True,
            "path": relative.as_posix(),
            "content": path.read_text(encoding="utf-8"),
        }

