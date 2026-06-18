from __future__ import annotations

import json
from typing import Iterable

from agent.llm_client import LLMClient
from agent.memory import FileMemoryStore
from agent.prompt import build_prompt_messages
from agent.schemas import (
    ACTION_FINAL_ANSWER,
    ACTION_TASK_UPDATE,
    ACTION_TOOL_CALL,
    MAX_REPAIR_ATTEMPTS,
    MAX_STEPS,
    validate_action_schema,
)
from agent.trace import TraceLogger
from tools.calculator import CalculatorTool
from tools.read_docs import ReadDocsTool
from tools.search_mock import SearchMockTool
from tools.todo import TodoTool


class AgentRuntime:
    """Local agent loop that parses JSON actions and executes tools itself."""

    def __init__(
        self,
        llm_client: object | None = None,
        tools: Iterable[object] | None = None,
        memory: FileMemoryStore | None = None,
        trace_dir: str = "data/traces",
        max_steps: int = MAX_STEPS,
    ):
        self.llm_client = llm_client or LLMClient()
        self.memory = memory or FileMemoryStore()
        self.max_steps = max_steps
        tool_list = list(tools) if tools is not None else self._default_tools()
        self.tools = {tool.name: tool for tool in tool_list}
        self.trace_dir = trace_dir

    def run_turn(self, user_input: str, session_id: str) -> str:
        trace = TraceLogger(session_id=session_id, user_input=user_input, trace_dir=self.trace_dir)
        observations: list[dict] = []
        self.memory.append_message(session_id, "user", user_input)

        try:
            for step_number in range(1, self.max_steps + 1):
                messages = build_prompt_messages(
                    user_input=user_input,
                    recent_messages=self.memory.get_recent_messages(session_id),
                    active_tasks=self.memory.get_active_tasks(session_id),
                    observations=observations,
                )
                llm_output = self.llm_client.complete(messages)
                action, parse_error = self._parse_action(llm_output)
                if parse_error:
                    should_continue = self._record_repairable_error(
                        trace=trace,
                        observations=observations,
                        step_number=step_number,
                        raw_llm_output=llm_output,
                        parse_error=parse_error,
                        schema_error=None,
                    )
                    if should_continue:
                        continue
                    return self._finish_with_fallback(trace, session_id, "parse_error", parse_error)

                schema_error = validate_action_schema(action, set(self.tools))
                if not schema_error:
                    schema_error = self._validate_content_directive(action, user_input)
                if schema_error:
                    should_continue = self._record_repairable_error(
                        trace=trace,
                        observations=observations,
                        step_number=step_number,
                        raw_llm_output=llm_output,
                        parse_error=None,
                        schema_error=schema_error,
                        action=action,
                    )
                    if should_continue:
                        continue
                    return self._finish_with_fallback(trace, session_id, "schema_error", schema_error)

                action_name = action.get("action")
                if action_name == ACTION_FINAL_ANSWER:
                    answer = action["answer"]
                    trace.add_step(
                        {
                            "step": step_number,
                            "raw_llm_output": llm_output,
                            "llm_output": llm_output,
                            "action": action,
                            "parse_error": None,
                            "schema_error": None,
                            "repair_attempt": None,
                        }
                    )
                    trace.set_final_answer(answer)
                    self.memory.append_message(session_id, "assistant", answer)
                    trace.save()
                    return answer

                if action_name == ACTION_TOOL_CALL:
                    observation, step = self._handle_tool_call(action, session_id, llm_output, step_number)
                    observations.append(observation)
                    trace.add_step(step)
                    continue

                if action_name == ACTION_TASK_UPDATE:
                    observation, step = self._handle_task_update(action, session_id, llm_output, step_number)
                    observations.append(observation)
                    trace.add_step(step)
                    continue

            return self._finish_with_error(
                trace,
                session_id,
                f"Reached max steps ({self.max_steps}) without final_answer.",
            )
        except Exception as exc:
            return self._finish_with_error(trace, session_id, f"Runtime error: {exc}")

    def _handle_tool_call(
        self, action: dict, session_id: str, llm_output: str, step_number: int
    ) -> tuple[dict, dict]:
        tool_name = action.get("tool_name")
        tool_args = action.get("tool_args", {})
        if not isinstance(tool_args, dict):
            tool_result = {"ok": False, "error": "tool_args must be an object"}
        elif tool_name not in self.tools:
            tool_result = {"ok": False, "error": f"Unknown tool: {tool_name}"}
        else:
            try:
                tool_result = self.tools[tool_name].run(
                    tool_args,
                    session={"session_id": session_id, "memory": self.memory},
                )
            except Exception as exc:
                tool_result = {"ok": False, "error": f"Tool error: {exc}"}

        observation = {"type": "tool_result", "tool_name": tool_name, "tool_result": tool_result}
        step = {
            "step": step_number,
            "raw_llm_output": llm_output,
            "llm_output": llm_output,
            "action": action,
            "parse_error": None,
            "schema_error": None,
            "repair_attempt": None,
            "tool_name": tool_name,
            "tool_args": tool_args,
            "tool_result": tool_result,
            "error": None if tool_result.get("ok") else tool_result.get("error"),
        }
        return observation, step

    def _handle_task_update(
        self, action: dict, session_id: str, llm_output: str, step_number: int
    ) -> tuple[dict, dict]:
        task_payload = action.get("task", {})
        if not isinstance(task_payload, dict):
            task_result = {"ok": False, "error": "task must be an object"}
        else:
            task = self.memory.upsert_task(session_id, task_payload)
            task_result = {"ok": True, "task": task}

        observation = {"type": "task_update", "result": task_result}
        step = {
            "step": step_number,
            "raw_llm_output": llm_output,
            "llm_output": llm_output,
            "action": action,
            "parse_error": None,
            "schema_error": None,
            "repair_attempt": None,
            "tool_name": None,
            "tool_args": None,
            "tool_result": task_result,
            "error": None if task_result.get("ok") else task_result.get("error"),
        }
        return observation, step

    def _record_repairable_error(
        self,
        trace: TraceLogger,
        observations: list[dict],
        step_number: int,
        raw_llm_output: str,
        parse_error: str | None,
        schema_error: str | None,
        action: dict | None = None,
    ) -> bool:
        previous_attempts = self._count_repair_attempts(observations)
        repair_attempt = previous_attempts if previous_attempts >= MAX_REPAIR_ATTEMPTS else previous_attempts + 1
        step = {
            "step": step_number,
            "raw_llm_output": raw_llm_output,
            "llm_output": raw_llm_output,
            "action": action,
            "parse_error": parse_error,
            "schema_error": schema_error,
            "repair_attempt": repair_attempt,
            "tool_name": action.get("tool_name") if action else None,
            "tool_args": action.get("tool_args") if action else None,
            "error": parse_error or schema_error,
        }
        trace.add_step(step)

        if previous_attempts >= MAX_REPAIR_ATTEMPTS:
            return False

        observations.append(
            {
                "type": "repair_request",
                "parse_error": parse_error,
                "schema_error": schema_error,
                "repair_attempt": repair_attempt,
                "instruction": "Re-output exactly one valid JSON action. Do not include markdown or extra text.",
            }
        )
        return True

    @staticmethod
    def _count_repair_attempts(observations: list[dict]) -> int:
        return sum(1 for observation in observations if observation.get("type") == "repair_request")

    @staticmethod
    def _validate_content_directive(action: dict, user_input: str) -> str | None:
        marker = "请直接返回最终答案："
        if action.get("action") != ACTION_FINAL_ANSWER or marker not in user_input:
            return None

        expected = user_input.split(marker, 1)[1].strip()
        if not expected:
            return None
        if action.get("answer") != expected:
            return f"final_answer.answer must exactly equal: {expected}"
        return None

    def _finish_with_fallback(
        self, trace: TraceLogger, session_id: str, reason_type: str, reason: str
    ) -> str:
        answer = "抱歉，我无法生成合法 JSON action。请稍后重试，或换一种更明确的说法。"
        trace.set_error(f"{reason_type}: {reason}")
        trace.set_final_answer(answer)
        trace.set_fallback_answer(answer)
        self.memory.append_message(session_id, "assistant", answer)
        trace.save()
        return answer

    def _finish_with_error(
        self, trace: TraceLogger, session_id: str, error: str, step: dict | None = None
    ) -> str:
        if step:
            step.setdefault("raw_llm_output", step.get("llm_output"))
            step.setdefault("parse_error", None)
            step.setdefault("schema_error", None)
            step.setdefault("repair_attempt", None)
            trace.add_step(step)
        trace.set_error(error)
        trace.set_final_answer(error)
        self.memory.append_message(session_id, "assistant", error)
        trace.save()
        return error

    @staticmethod
    def _parse_action(raw: str) -> tuple[dict, str | None]:
        try:
            action = json.loads(raw)
        except json.JSONDecodeError as exc:
            return {}, str(exc)
        if not isinstance(action, dict):
            return {}, "top-level JSON value must be an object"
        return action, None

    @staticmethod
    def _default_tools() -> list[object]:
        return [CalculatorTool(), SearchMockTool(), ReadDocsTool(), TodoTool()]
