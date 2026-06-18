from agent.memory import FileMemoryStore
from tools.read_docs import ReadDocsTool
from tools.search_mock import SearchMockTool
from tools.todo import TodoTool


def test_search_mock_returns_matching_results():
    result = SearchMockTool().run({"query": "trace logging"})

    assert result["ok"] is True
    assert result["results"][0]["title"] == "Trace Logging"


def test_read_docs_reads_markdown_and_blocks_traversal(tmp_path):
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    (docs_dir / "guide.md").write_text("# Guide\n", encoding="utf-8")
    tool = ReadDocsTool(docs_dir=docs_dir)

    assert tool.run({"path": "guide.md"}) == {
        "ok": True,
        "path": "guide.md",
        "content": "# Guide\n",
    }
    blocked = tool.run({"path": "../README.md"})
    assert blocked["ok"] is False
    assert "traversal" in blocked["error"]


def test_todo_tool_creates_lists_and_updates_session_tasks(tmp_path):
    memory = FileMemoryStore(base_dir=tmp_path / "sessions")
    session = {"memory": memory, "session_id": "demo"}
    tool = TodoTool()

    created = tool.run({"operation": "create", "title": "Write README"}, session=session)
    listed = tool.run({"operation": "list"}, session=session)
    updated = tool.run(
        {
            "operation": "update",
            "task_id": created["task"]["task_id"],
            "status": "done",
            "notes": "Completed.",
        },
        session=session,
    )

    assert created["ok"] is True
    assert listed["tasks"] == [created["task"]]
    assert updated["task"]["status"] == "done"
    assert memory.load_session("demo")["tasks"][0]["status"] == "done"
