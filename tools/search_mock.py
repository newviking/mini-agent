from __future__ import annotations

from tools.base import BaseTool


class SearchMockTool(BaseTool):
    name = "search_mock"
    description = "Return preset local search results for a query."

    knowledge_base = [
        {
            "title": "Agent Runtime Loop",
            "snippet": "A minimal runtime loads memory, asks an LLM for JSON actions, executes tools, and returns a final answer.",
        },
        {
            "title": "Session Memory",
            "snippet": "Session files keep recent messages and task state in data/sessions/{session_id}.json.",
        },
        {
            "title": "Trace Logging",
            "snippet": "Each user turn writes a trace file with LLM actions, tool calls, observations, errors, and final answers.",
        },
        {
            "title": "Tool Dispatch",
            "snippet": "The local runtime executes calculator, search_mock, read_docs, and todo from JSON tool_call actions.",
        },
    ]

    def run(self, args: dict, session: dict | None = None) -> dict:
        query = args.get("query")
        if not isinstance(query, str) or not query.strip():
            return {"ok": False, "error": "query is required"}

        terms = [term for term in query.lower().split() if term]
        scored = []
        for item in self.knowledge_base:
            text = f"{item['title']} {item['snippet']}".lower()
            score = sum(1 for term in terms if term in text)
            if score:
                scored.append((score, item))

        results = [item for _, item in sorted(scored, key=lambda pair: pair[0], reverse=True)]
        if not results:
            results = self.knowledge_base[:2]
        return {"ok": True, "results": results[:3]}

