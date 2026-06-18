from __future__ import annotations

import os


DEFAULT_LLM_BASE_URL = "https://maas-api.cn-huabei-1.xf-yun.com/v2"
DEFAULT_LLM_MODEL = "xopqwen35v35b"


class LLMClient:
    """Small wrapper around an OpenAI-compatible LLM API."""

    def __init__(self, model: str | None = None):
        try:
            from dotenv import load_dotenv
        except ImportError as exc:
            raise RuntimeError("python-dotenv is not installed. Run: pip install -r requirements.txt") from exc

        load_dotenv()
        api_key = os.getenv("LLM_API_KEY")
        if not api_key:
            raise RuntimeError("LLM_API_KEY is not set. Copy .env.example to .env and add your key.")

        try:
            from openai import OpenAI
        except ImportError as exc:
            raise RuntimeError("openai is not installed. Run: pip install -r requirements.txt") from exc

        self.model = model or os.getenv("LLM_MODEL", DEFAULT_LLM_MODEL)
        self.client = OpenAI(api_key=api_key, base_url=os.getenv("LLM_BASE_URL", DEFAULT_LLM_BASE_URL))

    def complete(self, messages: list[dict]) -> str:
        response = self.client.chat.completions.create(model=self.model, messages=messages)
        if not getattr(response, "choices", None):
            return ""

        message = response.choices[0].message
        return (getattr(message, "content", "") or "").strip()
