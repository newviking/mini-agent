MAX_STEPS = 6
MAX_REPAIR_ATTEMPTS = 2

ACTION_FINAL_ANSWER = "final_answer"
ACTION_TOOL_CALL = "tool_call"
ACTION_TASK_UPDATE = "task_update"

ALLOWED_ACTIONS = {ACTION_FINAL_ANSWER, ACTION_TOOL_CALL, ACTION_TASK_UPDATE}
TASK_STATUSES = {"in_progress", "done", "blocked"}


def validate_action_schema(action: dict, allowed_tools: set[str]) -> str | None:
    action_name = action.get("action")
    if action_name not in ALLOWED_ACTIONS:
        return "action must be one of: final_answer, tool_call, task_update"

    if action_name == ACTION_FINAL_ANSWER:
        if "answer" not in action:
            return "final_answer must include string field: answer"
        if not isinstance(action["answer"], str):
            return "final_answer.answer must be a string"
        return None

    if action_name == ACTION_TOOL_CALL:
        tool_name = action.get("tool_name")
        if tool_name not in allowed_tools:
            return "tool_name must be one of: " + ", ".join(sorted(allowed_tools))
        if "tool_args" not in action:
            return "tool_call must include dict field: tool_args"
        if not isinstance(action["tool_args"], dict):
            return "tool_call.tool_args must be a dict"
        return None

    task = action.get("task")
    if not isinstance(task, dict):
        return "task_update must include task object"
    return None
