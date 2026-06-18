# mini-runtime-agent

`mini-runtime-agent` 是一个用 Python 实现的最小可用 Agent Runtime 项目。它不依赖 LangChain、OpenHands、AutoGen 等现成 Agent 框架；Agent 主循环、JSON action 解析、工具调度、session memory、trace 日志和异常处理都由本地代码实现。

LLM 接入使用 OpenAI Python SDK 作为兼容 OpenAI 协议的 HTTP 客户端，请求目标是 LLMapi。

## 运行方式

在项目根目录执行以下命令：

| 命令 | 功能 |
| --- | --- |
| `cd D:\...` | 进入项目目录。 |
| `python -m pip install -r requirements.txt` | 安装 OpenAI SDK、python-dotenv、pytest 等依赖。 |
| `Copy-Item .env.example .env` | 在 Windows PowerShell 中复制环境变量模板。 |
| `cp .env.example .env` | 在 macOS/Linux/Git Bash 中复制环境变量模板。 |
| `notepad .env` | 打开本地环境变量文件，填写 `LLM_API_KEY` 等配置。 |
| `python main.py --session demo` | 启动 Agent CLI，并使用 `demo` 作为 session_id。 |
| `exit` 或 `quit` | 在 CLI 中退出当前交互。 |
| `python -m pytest tests -q` | 运行自动化测试，验证核心功能。 |

常用启动流程示例：

```powershell
cd D:\PythonProjects\mini-runtime-agent
python -m pip install -r requirements.txt
Copy-Item .env.example .env
notepad .env
python main.py --session demo
```

如果 `.env` 已经配置好，后续只需要执行 `python main.py --session demo` 即可进入 CLI。

## 环境变量配置

`.env` 文件内容示例：

```env
LLM_API_KEY=your_llm_api_key_here
LLM_BASE_URL=https://maas-api.cn-huabei-1.xf-yun.com/v2
LLM_MODEL=xopqwen35v35b
```

说明：

- `LLM_API_KEY`：LLMapi 的真实 APIKey。
- `LLM_BASE_URL`：LLMapi 接口地址，默认是 `https://maas-api.cn-huabei-1.xf-yun.com/v2`。
- `LLM_MODEL`：模型名称，当前默认是 `xopqwen35v35b`。

`.env` 已加入 `.gitignore`，不要把真实 APIKey 提交到代码仓库。

## 系统设计

项目由几个小模块组成：

- `main.py`：CLI 入口，读取用户输入并调用 `AgentRuntime.run_turn`。
- `agent/runtime.py`：实现 Agent 主循环、action 解析、schema 校验、工具调用、修复重试和 trace 写入。
- `agent/llm_client.py`：封装 LLMapi 调用，返回模型输出文本。
- `agent/prompt.py`：构造 system prompt，注入 recent messages、active tasks 和 observation。
- `agent/memory.py`：使用本地 JSON 文件保存 session messages 和 tasks。
- `agent/trace.py`：每轮对话生成一个 trace JSON 文件。
- `tools/`：本地工具实现，包括 calculator、search_mock、read_docs、todo。

模型只负责输出自定义 JSON action；工具执行由本地 runtime 完成，不使用模型服务商内置 function calling。

## Agent Loop 流程

每次用户输入都会执行以下流程：

1. 将用户消息写入当前 session。
2. 从 session 中读取 recent messages 和 active tasks。
3. 构造 prompt，要求模型只输出 JSON action。
4. 调用真实 LLM API。
5. 解析模型输出 JSON。
6. 校验 action schema。
7. 根据 action 类型执行：
   - `final_answer`：保存并返回最终回答。
   - `tool_call`：本地执行工具，并把工具结果作为 observation 继续交给 LLM。
   - `task_update`：更新当前 session 的 task state。
8. 循环直到模型输出 `final_answer` 或达到最大步数 `MAX_STEPS = 6`。
9. 保存本轮 trace 到 `data/traces/`。

## JSON Action 协议

支持三类 action：

```json
{"action": "final_answer", "answer": "给用户的最终回答"}
```

```json
{"action": "tool_call", "tool_name": "calculator", "tool_args": {"expression": "2 + 2"}}
```

```json
{
  "action": "task_update",
  "task": {
    "task_id": "task_xxx",
    "title": "任务标题",
    "status": "in_progress",
    "notes": "任务说明"
  }
}
```

runtime 会校验：

- `action` 只能是 `final_answer`、`tool_call`、`task_update`。
- `final_answer.answer` 必须是字符串。
- `tool_call.tool_name` 必须在工具白名单内。
- `tool_call.tool_args` 必须是 dict。
- `task_update.task` 必须是对象。

如果模型输出非法 JSON 或 action schema 不合法，runtime 会把错误作为 observation 反馈给 LLM，最多自动修复重试 2 次。超过重试次数后，runtime 返回 fallback final answer，并把错误写入 trace。

## 工具系统

内置工具：

- `calculator`：使用 `ast` 安全计算数学表达式，支持数字、`+`、`-`、`*`、`/`、`**`、`%` 和括号，不使用 `eval`。
- `search_mock`：本地 mock 搜索，根据关键词返回预置结果。
- `read_docs`：读取 `docs/` 目录下的 Markdown 文件，并阻止路径穿越。
- `todo`：在当前 session 中创建、列出、更新任务，用于跨轮次继续执行。

工具调用由模型输出 JSON action 触发，但真正执行工具的是本地 runtime。

## Memory 召回时机

memory 会在每次 LLM 调用前召回。runtime 会读取：

- `get_recent_messages(session_id)`：最近的用户和助手消息。
- `get_active_tasks(session_id)`：状态不是 `done` 的任务。

如果某一步执行了工具或更新了任务，下一次 LLM 调用会拿到新的 observation 和更新后的 session context。

## Memory 放置方式

每个 session 保存到：

```text
data/sessions/{session_id}.json
```

session 文件结构示例：

```json
{
  "session_id": "demo",
  "messages": [
    {"role": "user", "content": "..."},
    {"role": "assistant", "content": "..."}
  ],
  "tasks": [
    {
      "task_id": "task_1234abcd",
      "title": "整理 README",
      "status": "in_progress",
      "notes": "包括运行方式、系统设计和 memory 说明"
    }
  ]
}
```

重新运行同一个 session，例如 `python main.py --session demo`，runtime 会重新加载这个文件，因此可以继续之前的任务。

## Trace 日志格式

每轮对话都会在 `data/traces/` 下生成一个 JSON trace 文件。文件名包含时间戳、session_id 和 trace_id。

trace 内容示例：

```json
{
  "trace_id": "trace_xxx",
  "created_at": "2026-06-18T00:00:00+00:00",
  "session_id": "demo",
  "user_input": "calculate 2 + 2",
  "steps": [
    {
      "step": 1,
      "raw_llm_output": "{\"action\":\"tool_call\"...}",
      "action": {},
      "parse_error": null,
      "schema_error": null,
      "repair_attempt": null,
      "tool_name": "calculator",
      "tool_args": {"expression": "2 + 2"},
      "tool_result": {"ok": true, "result": 4},
      "error": null
    }
  ],
  "final_answer": "2 + 2 = 4",
  "fallback_answer": null,
  "error": null
}
```

当模型输出非法 JSON 或非法 action schema 时，trace 中会记录 `parse_error`、`schema_error` 和 `repair_attempt`。如果最终进入 fallback，`fallback_answer` 会保存返回给用户的兜底回答。

## 跨轮次继续执行示例

第一轮：

```text
> 请帮我创建一个任务：整理这个 Agent 项目的 README，要求包括运行方式、系统设计和 memory 说明。
任务“整理 Agent 项目 README”已创建并设为进行中。
```

第二轮，使用同一个 session：

```text
> 继续刚才的 README 任务，现在帮我列出目录。
基于当前 active tasks，README 目录建议为：项目简介、运行方式、系统设计、Agent loop、工具系统、memory 说明、trace 日志和演示步骤。
```

第二轮能够继续处理，是因为任务状态已经保存在 `data/sessions/demo.json` 中。

## 演示步骤

以下步骤适合用于终端录屏演示。录屏时不要打开 `.env` 文件，避免暴露真实 APIKey。

| 步骤 | 命令或输入 | 用途 |
| --- | --- | --- |
| 1 | `cd D:\PythonProjects\mini-runtime-agent` | 进入项目目录。 |
| 2 | `python -m pip install -r requirements.txt` | 安装运行和测试依赖。 |
| 3 | `Copy-Item .env.example .env` | 首次运行时复制环境变量模板。 |
| 4 | `notepad .env` | 填写 `LLM_API_KEY`、`LLM_BASE_URL`、`LLM_MODEL`。录屏时不要展示文件内容。 |
| 5 | `python main.py --session demo` | 启动 CLI，并使用 `demo` 作为 session_id。 |
| 6 | `你好，请用一句话回复我。` | 演示普通问答直接返回 `final_answer`。 |
| 7 | `请直接返回最终答案：cli-ok` | 演示简单 CLI 指令服从和精确 final answer 校验。 |
| 8 | `请使用 calculator 工具计算 12 * (3 + 4)，并给出最终答案。` | 演示 LLM 触发 `calculator` 工具，本地 runtime 执行工具并返回结果。 |
| 9 | `搜索 runtime trace logging` | 演示 `search_mock` 本地 mock 搜索工具。 |
| 10 | `请帮我创建一个任务：整理这个 Agent 项目的 README，要求包括运行方式、系统设计和 memory 说明。` | 演示 `todo` 任务创建，并把 task state 写入 session。 |
| 11 | `exit` | 退出当前 CLI，准备演示跨轮次恢复。 |
| 12 | `python main.py --session demo` | 使用同一个 session 重新启动 CLI。 |
| 13 | `继续刚才的 README 任务，现在帮我列出目录。` | 演示从 `data/sessions/demo.json` 召回 active tasks 并继续执行。 |
| 14 | `exit` | 退出 CLI。 |
| 15 | `Get-Content data\sessions\demo.json -Encoding UTF8` | 查看 session 文件，确认 messages 和 tasks 已持久化。 |
| 16 | `Get-ChildItem data\traces | Sort-Object LastWriteTime -Descending | Select-Object -First 5` | 查看最近生成的 trace 文件列表。 |
| 17 | `Get-ChildItem data\traces | Sort-Object LastWriteTime -Descending | Select-Object -First 1 | Get-Content -Encoding UTF8` | 查看最新 trace 内容，确认 action、tool_result、parse_error、schema_error、final_answer 等字段。 |
| 18 | `python -m pytest tests -q -p no:cacheprovider --basetemp .pytest-run-demo` | 运行自动化测试，验证核心功能。 |

## 稳定性优化说明

项目核心流程已通过 LLMapi 真实请求验证：prompt 构造、JSON action 解析、本地工具执行、memory 持久化、trace 记录和跨轮次任务续接都可以端到端跑通。

简单自由 CLI 问答仍然存在一定不稳定性，因为 LLM 输出具有概率性，尤其是较小模型可能偶尔不严格遵守 JSON action 协议。项目已通过 schema 校验、自动修复重试、工具白名单、普通问答直接回答优先规则、精确 final answer 指令校验和更完整的 trace 记录进行优化。这些措施无法 100% 消除无效模型输出，但已经满足最小可用 Agent Runtime 的稳定演示要求。

## 测试

运行测试：

```bash
python -m pytest tests -q
```

如果 Windows 临时目录权限导致 pytest 的 `tmp_path` 失败，可以指定项目内临时目录：

```powershell
python -m pytest tests -q -p no:cacheprovider --basetemp .pytest-basetemp
```
