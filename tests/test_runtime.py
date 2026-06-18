import json

from agent.memory import FileMemoryStore
from agent.runtime import AgentRuntime
from tools.calculator import CalculatorTool


class FakeLLMClient:
    def __init__(self, responses):
        self.responses = list(responses)
        self.prompts = []

    def complete(self, messages):
        self.prompts.append(messages)
        return self.responses.pop(0)


def test_runtime_executes_tool_call_then_returns_final_answer(tmp_path):
    llm = FakeLLMClient(
        [
            json.dumps(
                {
                    "action": "tool_call",
                    "tool_name": "calculator",
                    "tool_args": {"expression": "2 + 2"},
                }
            ),
            json.dumps({"action": "final_answer", "answer": "2 + 2 = 4"}),
        ]
    )
    memory = FileMemoryStore(base_dir=tmp_path / "sessions")
    runtime = AgentRuntime(
        llm_client=llm,
        tools=[CalculatorTool()],
        memory=memory,
        trace_dir=tmp_path / "traces",
    )

    answer = runtime.run_turn("calculate 2 + 2", session_id="demo")

    assert answer == "2 + 2 = 4"
    saved = memory.load_session("demo")
    assert saved["messages"] == [
        {"role": "user", "content": "calculate 2 + 2"},
        {"role": "assistant", "content": "2 + 2 = 4"},
    ]
    trace_files = list((tmp_path / "traces").glob("*.json"))
    assert len(trace_files) == 1
    trace = json.loads(trace_files[0].read_text(encoding="utf-8"))
    assert trace["session_id"] == "demo"
    assert trace["final_answer"] == "2 + 2 = 4"
    assert trace["steps"][0]["tool_name"] == "calculator"
    assert trace["steps"][0]["tool_result"] == {"ok": True, "result": 4}


def test_runtime_handles_invalid_json_without_crashing(tmp_path):
    llm = FakeLLMClient(["not json", json.dumps({"action": "final_answer", "answer": "recovered"})])
    memory = FileMemoryStore(base_dir=tmp_path / "sessions")
    runtime = AgentRuntime(
        llm_client=llm,
        tools=[CalculatorTool()],
        memory=memory,
        trace_dir=tmp_path / "traces",
    )

    answer = runtime.run_turn("hello", session_id="demo")

    assert answer == "recovered"
    assert "parse_error" in llm.prompts[1][-1]["content"]
    trace_files = list((tmp_path / "traces").glob("*.json"))
    trace = json.loads(trace_files[0].read_text(encoding="utf-8"))
    assert trace["error"] is None
    assert trace["steps"][0]["raw_llm_output"] == "not json"
    assert trace["steps"][0]["parse_error"]
    assert trace["steps"][0]["repair_attempt"] == 1


def test_runtime_falls_back_after_repair_attempts_are_exhausted(tmp_path):
    llm = FakeLLMClient(["not json", "still not json", "again not json"])
    memory = FileMemoryStore(base_dir=tmp_path / "sessions")
    runtime = AgentRuntime(
        llm_client=llm,
        tools=[CalculatorTool()],
        memory=memory,
        trace_dir=tmp_path / "traces",
    )

    answer = runtime.run_turn("hello", session_id="demo")

    assert "无法生成合法 JSON action" in answer
    trace = json.loads(next((tmp_path / "traces").glob("*.json")).read_text(encoding="utf-8"))
    assert trace["fallback_answer"] == answer
    assert trace["steps"][-1]["repair_attempt"] == 2


def test_runtime_retries_invalid_tool_name_without_executing_tool(tmp_path):
    llm = FakeLLMClient(
        [
            json.dumps({"action": "tool_call", "tool_name": "shell", "tool_args": {}}),
            json.dumps({"action": "final_answer", "answer": "I cannot use that tool."}),
        ]
    )
    memory = FileMemoryStore(base_dir=tmp_path / "sessions")
    runtime = AgentRuntime(
        llm_client=llm,
        tools=[CalculatorTool()],
        memory=memory,
        trace_dir=tmp_path / "traces",
    )

    answer = runtime.run_turn("run shell", session_id="demo")

    assert answer == "I cannot use that tool."
    assert "schema_error" in llm.prompts[1][-1]["content"]
    trace = json.loads(next((tmp_path / "traces").glob("*.json")).read_text(encoding="utf-8"))
    assert "tool_name must be one of" in trace["steps"][0]["schema_error"]
    assert trace["steps"][0]["tool_name"] == "shell"
    assert "tool_result" not in trace["steps"][0]


def test_runtime_continues_todo_task_across_turns(tmp_path):
    llm = FakeLLMClient(
        [
            json.dumps(
                {
                    "action": "tool_call",
                    "tool_name": "todo",
                    "tool_args": {
                        "operation": "create",
                        "title": "整理 README",
                        "notes": "包括运行方式、系统设计和 memory 说明",
                    },
                }
            ),
            json.dumps({"action": "final_answer", "answer": "README task created."}),
            json.dumps({"action": "final_answer", "answer": "Continuing README task outline."}),
        ]
    )
    memory = FileMemoryStore(base_dir=tmp_path / "sessions")
    runtime = AgentRuntime(
        llm_client=llm,
        memory=memory,
        trace_dir=tmp_path / "traces",
    )

    first_answer = runtime.run_turn("创建 README 任务", session_id="demo")
    second_answer = runtime.run_turn("继续刚才的 README 任务", session_id="demo")

    assert first_answer == "README task created."
    assert second_answer == "Continuing README task outline."
    assert memory.get_active_tasks("demo")[0]["title"] == "整理 README"
    second_turn_prompt = llm.prompts[-1][1]["content"]
    assert "整理 README" in second_turn_prompt
    assert "active_tasks" in second_turn_prompt


def test_runtime_repairs_direct_final_answer_mismatch(tmp_path):
    llm = FakeLLMClient(
        [
            json.dumps({"action": "final_answer", "answer": "How can I help?"}),
            json.dumps({"action": "final_answer", "answer": "cli-ok"}),
        ]
    )
    memory = FileMemoryStore(base_dir=tmp_path / "sessions")
    runtime = AgentRuntime(
        llm_client=llm,
        tools=[CalculatorTool()],
        memory=memory,
        trace_dir=tmp_path / "traces",
    )

    answer = runtime.run_turn("请直接返回最终答案：cli-ok", session_id="demo")

    assert answer == "cli-ok"
    assert "schema_error" in llm.prompts[1][-1]["content"]
    trace = json.loads(next((tmp_path / "traces").glob("*.json")).read_text(encoding="utf-8"))
    assert "final_answer.answer must exactly equal" in trace["steps"][0]["schema_error"]
