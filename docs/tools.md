# Tools

Tools implement `BaseTool`:

```python
class BaseTool:
    name: str
    description: str

    def run(self, args: dict, session: dict | None = None) -> dict:
        ...
```

## calculator

Input:

```json
{"expression": "2 + 3 * 4"}
```

Output:

```json
{"ok": true, "result": 14}
```

The implementation uses Python `ast` and only permits arithmetic nodes. It rejects function calls, names, imports, attributes, and other non-arithmetic expressions.

## search_mock

Input:

```json
{"query": "runtime memory"}
```

Output:

```json
{"ok": true, "results": [{"title": "...", "snippet": "..."}]}
```

The search is local and deterministic.

## read_docs

Input:

```json
{"path": "agent_design.md"}
```

Output:

```json
{"ok": true, "path": "agent_design.md", "content": "..."}
```

Only `.md` files inside `docs/` can be read. Path traversal is blocked.

## todo

Operations:

- `create`: create a task in the current session.
- `list`: list all tasks in the current session.
- `update`: update task status, notes, or title.

Example:

```json
{"operation": "create", "title": "Write README", "notes": "Include design and memory."}
```

