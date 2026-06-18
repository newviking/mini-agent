# Demo Transcript

```text
$ python main.py --session demo
mini-runtime-agent session=demo
Type exit or quit to stop.

> Calculate 18 * (7 + 3).
18 * (7 + 3) = 180.

Trace excerpt:
LLM action: {"action":"tool_call","tool_name":"calculator","tool_args":{"expression":"18 * (7 + 3)"}}
Tool result: {"ok": true, "result": 180}

> Search locally for runtime trace logging.
I found local notes about Trace Logging: each user turn writes a trace file with LLM actions, tool calls, observations, errors, and final answers.

Trace excerpt:
LLM action: {"action":"tool_call","tool_name":"search_mock","tool_args":{"query":"runtime trace logging"}}
Tool result: {"ok": true, "results": [{"title": "Trace Logging", "snippet": "..."}]}

> Please create a task: organize this Agent project's README, including run steps, system design, and memory notes.
Created an active README task with notes for run steps, system design, and memory.

Trace excerpt:
LLM action: {"action":"tool_call","tool_name":"todo","tool_args":{"operation":"create","title":"Organize README","notes":"Include run steps, system design, and memory notes."}}
Tool result: {"ok": true, "task": {"task_id": "task_1234abcd", "title": "Organize README", "status": "in_progress", "notes": "..."}}

> Continue the README task from before. List the outline now.
Continuing the active README task. Suggested outline: project overview, run steps, environment variables, system design, agent loop, tools, memory recall and placement, trace format, cross-turn demo, screen recording, and submission notes.

> exit
```

