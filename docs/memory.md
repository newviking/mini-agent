# Memory

Memory is stored in local JSON files under `data/sessions/`.

## Session File

Each file is named `{session_id}.json` and contains:

- `session_id`: the selected CLI session.
- `messages`: ordered user and assistant messages.
- `tasks`: task objects used for cross-turn continuation.

## Recall Timing

The runtime recalls memory before each LLM call. It injects recent messages and active tasks into the prompt. Active tasks are tasks whose status is not `done`.

This means a second CLI run with the same session id can continue work created in a previous run.

## Placement in Prompt

`agent/prompt.py` packages memory as JSON under `Session context`. The LLM sees:

- `current_user_input`
- `recent_messages`
- `active_tasks`

Tool observations are appended as separate `Observation` messages in the same LLM step loop.

