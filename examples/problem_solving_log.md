# Problem Solving Log

## LLM outputs non-JSON

Problem: The runtime cannot assume the model will always obey the JSON-only instruction.

Solution: `AgentRuntime._parse_action` catches `JSONDecodeError`. The turn returns a clear error message, appends it to session memory, and writes the raw LLM output plus error to the trace.

## Tool call fails

Problem: A model may request an unknown tool, pass non-object arguments, or a tool may raise internally.

Solution: Runtime tool dispatch checks the tool name and argument type before execution. Tool exceptions are caught and converted to `{"ok": false, "error": "..."}` observations. The trace stores the failing tool call and error.

## Cross-turn task cannot be recalled

Problem: Follow-up prompts such as "continue the README task" fail if task state only lives in the current process.

Solution: The `todo` tool and `task_update` action write tasks into `data/sessions/{session_id}.json`. Each LLM step injects `active_tasks`, so restarting the CLI with the same session id preserves task context.

## 简单 CLI 问答中指令服从稳定性一般

### 问题描述

真实 LLMapi 测试中，简单 CLI 问答有时没有严格按用户期望返回指定内容。模型可能输出非 JSON、输出 JSON 但字段不完整，或者在不需要工具时错误选择工具调用。这会影响演示时的稳定性。

### 原因分析

LLM 输出具有概率性，尤其在自由问答场景中，模型可能更倾向于普通聊天格式，而不是严格遵守 runtime 要求的 JSON action 协议。原始实现只做 JSON 解析，缺少 action schema 校验，也缺少把错误反馈给模型进行自动修复的机制。

### 已采取的解决措施

1. 新增 action schema 校验，限制 action 只能是 `final_answer`、`tool_call`、`task_update`。
2. 校验 `final_answer.answer`、`tool_call.tool_name`、`tool_call.tool_args`、`task_update.task` 等关键字段。
3. 对工具名增加白名单，只允许 `calculator`、`search_mock`、`read_docs`、`todo`。
4. JSON 解析失败或 schema 校验失败时，将错误作为 observation 反馈给 LLM，并最多自动修复重试 2 次。
5. trace 增加 `raw_llm_output`、`parse_error`、`schema_error`、`repair_attempt` 和 `fallback_answer`，便于复盘。
6. system prompt 增加直接回答优先规则和 few-shot 示例，引导普通聊天走 `final_answer`。

### 后续优化方案

可以继续增加更细的 action schema、对常见普通问答做本地快速分类、提高 few-shot 覆盖范围，或在 CLI 中加入调试模式展示每一步 action 和 observation。若接入更强的模型，也可以进一步提升 JSON action 稳定性。

### 结论

该问题无法在概率模型层面 100% 消除，但当前 runtime 已具备本地 schema 防护、自动修复、fallback 和可追踪日志。项目已经满足最小可用 Agent Runtime 的稳定演示要求。
