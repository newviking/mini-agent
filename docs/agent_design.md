# Agent Design

The project implements a minimal local Agent Runtime. The LLM is only a text generator that emits custom JSON actions. The runtime parses those actions and decides whether to return a final answer, execute a local tool, or update task state.

## Modules

- `AgentRuntime` owns the turn loop, max-step limit, JSON parsing, local tool dispatch, observations, and trace saving.
- `LLMClient` wraps the OpenAI-compatible LLMapi chat completions endpoint.
- `FileMemoryStore` persists session messages and tasks as JSON files.
- `TraceLogger` records every step in one JSON trace file per turn.
- `tools/` provides local tool implementations behind a common `BaseTool` interface.

## Control Flow

1. The CLI sends `user_input` and `session_id` to `run_turn`.
2. Memory stores the user message.
3. Prompt construction injects recent messages and active tasks.
4. The LLM returns one JSON action.
5. Runtime parses and validates the action.
6. Tool calls are executed locally and returned as observations.
7. The loop repeats until `final_answer` or `MAX_STEPS`.

## Error Handling

Invalid JSON, unknown actions, missing tools, invalid tool args, tool exceptions, and max-step exhaustion are handled without crashing the CLI. Each error is written into the trace.
