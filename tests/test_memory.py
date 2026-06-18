from agent.memory import FileMemoryStore


def test_memory_creates_session_with_messages_and_tasks(tmp_path):
    memory = FileMemoryStore(base_dir=tmp_path / "sessions")

    session = memory.load_session("demo")

    assert session["session_id"] == "demo"
    assert session["messages"] == []
    assert session["tasks"] == []


def test_memory_appends_messages_and_persists_tasks(tmp_path):
    memory = FileMemoryStore(base_dir=tmp_path / "sessions")

    memory.append_message("demo", "user", "hello")
    task = memory.upsert_task(
        "demo",
        {
            "title": "Write README",
            "status": "in_progress",
            "notes": "Include runtime and memory sections.",
        },
    )

    loaded = memory.load_session("demo")

    assert loaded["messages"] == [{"role": "user", "content": "hello"}]
    assert loaded["tasks"] == [task]
    assert task["task_id"].startswith("task_")


def test_memory_returns_recent_messages_and_active_tasks(tmp_path):
    memory = FileMemoryStore(base_dir=tmp_path / "sessions")
    for index in range(5):
        memory.append_message("demo", "user", f"message {index}")
    memory.upsert_task("demo", {"task_id": "task_done", "title": "Done", "status": "done"})
    memory.upsert_task(
        "demo",
        {"task_id": "task_active", "title": "Active", "status": "in_progress"},
    )

    assert [message["content"] for message in memory.get_recent_messages("demo", limit=2)] == [
        "message 3",
        "message 4",
    ]
    assert memory.get_active_tasks("demo") == [
        {"task_id": "task_active", "title": "Active", "status": "in_progress", "notes": ""}
    ]
