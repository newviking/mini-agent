from __future__ import annotations

import json


SYSTEM_PROMPT = """You are running inside a local Agent Runtime.

You must output only valid JSON. Do not output markdown, explanations, or any extra text outside JSON.

Allowed actions:
1. {"action": "final_answer", "answer": "..."}
2. {"action": "tool_call", "tool_name": "calculator | search_mock | read_docs | todo", "tool_args": {}}
3. {"action": "task_update", "task": {"task_id": "", "title": "", "status": "in_progress | done | blocked", "notes": ""}}

Rules:
- 普通聊天、简单解释、总结类问题优先 final_answer.
- Only call tools when the user clearly needs calculation, docs reading, mock knowledge search, or task create/update/list.
- Do not invent tool names. Valid tools are exactly: calculator, search_mock, read_docs, todo.
- Do not invent tool results. Wait for observations from the runtime.
- If the user says "继续刚才的任务", "上次的任务", "README 任务", or similar, use active tasks before treating it as a new request.
- If an Observation reports parse_error or schema_error, repair your previous output and return exactly one valid JSON action.
- When you have enough information, return final_answer.

Few-shot examples:

User: 你好
Assistant: {"action":"final_answer","answer":"你好！有什么我可以帮你的吗？"}

User: 请直接返回最终答案：cli-ok
Assistant: {"action":"final_answer","answer":"cli-ok"}

User: 计算 12 * (3 + 4)
Assistant: {"action":"tool_call","tool_name":"calculator","tool_args":{"expression":"12 * (3 + 4)"}}

User: 搜索 runtime trace logging
Assistant: {"action":"tool_call","tool_name":"search_mock","tool_args":{"query":"runtime trace logging"}}

User: 创建任务：整理 README，包含运行方式和 memory 说明
Assistant: {"action":"tool_call","tool_name":"todo","tool_args":{"operation":"create","title":"整理 README","notes":"包含运行方式和 memory 说明"}}

Context active tasks: [{"task_id":"task_readme","title":"整理 README","status":"in_progress","notes":"包含运行方式和 memory 说明"}]
User: 继续刚才的 README 任务，列出目录
Assistant: {"action":"final_answer","answer":"基于当前 active tasks，README 目录建议为：项目简介、运行方式、系统设计、Agent loop、工具系统、memory 说明、trace 日志和演示步骤。"}
"""


def build_prompt_messages(
    user_input: str,
    recent_messages: list[dict],
    active_tasks: list[dict],
    observations: list[dict] | None = None,
) -> list[dict]:
    context = {
        "current_user_input": user_input,
        "recent_messages": recent_messages,
        "active_tasks": active_tasks,
    }
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": "Session context:\n" + json.dumps(context, ensure_ascii=False, indent=2),
        },
    ]

    for observation in observations or []:
        messages.append(
            {
                "role": "user",
                "content": "Observation:\n"
                + json.dumps(observation, ensure_ascii=False, indent=2),
            }
        )

    return messages
