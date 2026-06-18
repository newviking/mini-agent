import sys
from types import SimpleNamespace

import pytest

from agent.llm_client import DEFAULT_LLM_BASE_URL, DEFAULT_LLM_MODEL, LLMClient


class FakeOpenAI:
    last_kwargs = None

    def __init__(self, **kwargs):
        FakeOpenAI.last_kwargs = kwargs
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    def _create(self, **kwargs):
        FakeOpenAI.last_create_kwargs = kwargs
        message = SimpleNamespace(content='{"action":"final_answer","answer":"ok"}')
        choice = SimpleNamespace(message=message)
        return SimpleNamespace(choices=[choice])


def install_fake_sdk(monkeypatch):
    monkeypatch.setitem(sys.modules, "dotenv", SimpleNamespace(load_dotenv=lambda: None))
    monkeypatch.setitem(sys.modules, "openai", SimpleNamespace(OpenAI=FakeOpenAI))


def test_llm_client_uses_llm_api_key_and_llm_base_url(monkeypatch):
    install_fake_sdk(monkeypatch)
    monkeypatch.setenv("LLM_API_KEY", "test-key")
    monkeypatch.setenv("LLM_BASE_URL", "https://example.test/v2")
    monkeypatch.setenv("LLM_MODEL", "demo-model")

    client = LLMClient()
    output = client.complete([{"role": "user", "content": "hi"}])

    assert FakeOpenAI.last_kwargs == {
        "api_key": "test-key",
        "base_url": "https://example.test/v2",
    }
    assert FakeOpenAI.last_create_kwargs["model"] == "demo-model"
    assert output == '{"action":"final_answer","answer":"ok"}'


def test_llm_client_defaults_to_llmapi_base_url(monkeypatch):
    install_fake_sdk(monkeypatch)
    monkeypatch.setenv("LLM_API_KEY", "test-key")
    monkeypatch.delenv("LLM_BASE_URL", raising=False)
    monkeypatch.delenv("LLM_MODEL", raising=False)

    client = LLMClient()
    client.complete([{"role": "user", "content": "hi"}])

    assert FakeOpenAI.last_kwargs["base_url"] == DEFAULT_LLM_BASE_URL
    assert FakeOpenAI.last_create_kwargs["model"] == DEFAULT_LLM_MODEL
    assert DEFAULT_LLM_MODEL == "xopqwen35v35b"


def test_llm_client_requires_llm_api_key(monkeypatch):
    install_fake_sdk(monkeypatch)
    monkeypatch.delenv("LLM_API_KEY", raising=False)

    with pytest.raises(RuntimeError, match="LLM_API_KEY"):
        LLMClient()
