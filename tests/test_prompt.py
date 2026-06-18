from agent.prompt import SYSTEM_PROMPT, build_prompt_messages


def test_prompt_guides_simple_greeting_toward_final_answer():
    messages = build_prompt_messages("你好", recent_messages=[], active_tasks=[])

    assert "普通聊天、简单解释、总结类问题优先 final_answer" in SYSTEM_PROMPT
    assert '{"action":"final_answer","answer":"你好！有什么我可以帮你的吗？"}' in SYSTEM_PROMPT
    assert messages[0]["role"] == "system"


def test_prompt_contains_required_few_shot_examples():
    assert "calculator" in SYSTEM_PROMPT
    assert "search_mock" in SYSTEM_PROMPT
    assert "todo" in SYSTEM_PROMPT
    assert "继续刚才的 README 任务" in SYSTEM_PROMPT
    assert "active tasks" in SYSTEM_PROMPT.lower()
