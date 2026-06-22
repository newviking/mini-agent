# 问题解决记录

## LLM 输出非 JSON

### 问题描述

runtime 要求 LLM 每一步只输出 JSON action，但真实模型不能保证始终严格遵守该格式。模型可能输出普通自然语言、Markdown，或者在 JSON 前后添加多余解释文本。

### 原因分析

LLM 输出具有概率性。即使 system prompt 明确要求只输出 JSON，模型仍可能受到用户问题、上下文或自身对话习惯影响，输出不符合 runtime 协议的内容。

### 已采取的解决措施

1. 在 `AgentRuntime._parse_action` 中捕获 `JSONDecodeError`，避免程序崩溃。
2. 将原始模型输出记录到 trace 的 `raw_llm_output` 字段。
3. 将解析错误记录到 trace 的 `parse_error` 字段。
4. 把解析错误作为 observation 反馈给 LLM，要求重新输出合法 JSON action。
5. 最多自动修复重试 2 次，超过后返回 fallback final answer。

### 结论

非法 JSON 不会导致 CLI 崩溃，runtime 可以自动尝试修复，并且所有失败信息都会写入 trace，便于复盘。

## 工具调用失败

### 问题描述

模型可能请求不存在的工具，或者传入错误类型的 `tool_args`。工具内部也可能因为参数缺失、文件不存在、表达式非法等原因执行失败。

### 原因分析

工具调用由 LLM 生成 JSON action 触发，模型并不真正理解本地工具实现细节。如果没有本地校验，错误工具名或错误参数可能进入工具执行阶段，影响稳定性。

### 已采取的解决措施

1. 新增 action schema 校验，`tool_call.tool_name` 必须在工具白名单内。
2. 工具白名单只允许 `calculator`、`search_mock`、`read_docs`、`todo`。
3. `tool_call.tool_args` 必须是 dict 类型。
4. 工具执行异常会被捕获，并转换为 `{"ok": false, "error": "..."}`。
5. 工具错误、工具名、参数和结果都会写入 trace。

### 结论

工具不存在、参数错误和工具内部异常都不会导致 runtime 崩溃，错误会被结构化记录，并可作为 observation 继续交给 LLM 处理。

## 跨轮次任务无法召回

### 问题描述

用户第一轮创建任务后，第二轮说“继续刚才的任务”或“继续 README 任务”时，如果任务状态只保存在进程内存中，重新启动 CLI 后就无法恢复上下文。

### 原因分析

跨轮次继续执行依赖持久化 memory。如果 session messages 和 tasks 没有保存到本地文件，Agent 就无法知道上一轮已经创建了什么任务。

### 已采取的解决措施

1. 使用 `data/sessions/{session_id}.json` 保存每个 session 的 messages 和 tasks。
2. `todo` 工具支持 create、list、update，所有任务都写入当前 session。
3. runtime 在每次 LLM 调用前注入 recent messages 和 active tasks。
4. system prompt 明确要求遇到“继续刚才的任务”“上次的任务”“README 任务”等表达时优先参考 active tasks。
5. 测试覆盖了 todo 任务创建和跨轮次继续场景。

### 结论

重新运行同一个 session 后，Agent 可以从本地 JSON session 文件中召回 active tasks，并基于已有任务继续处理。

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
7. 对“请直接返回最终答案：xxx”这类演示指令增加内容级校验，降低合法 JSON 但回答内容不符合要求的问题。

### 后续优化方案

可以继续增加更细的 action schema、对常见普通问答做本地快速分类、提高 few-shot 覆盖范围，或在 CLI 中加入调试模式展示每一步 action 和 observation。若接入更强的模型，也可以进一步提升 JSON action 稳定性。

### 结论

该问题无法在概率模型层面 100% 消除，但当前 runtime 已具备本地 schema 防护、自动修复、fallback、内容级校验和可追踪日志。项目已经满足最小可用 Agent Runtime 的稳定演示要求。
