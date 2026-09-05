from __future__ import annotations

import os
from typing import Protocol

from mini_agent.errors import LLMError


class LLMClient(Protocol):
    def complete(self, messages: list[dict]) -> str: ...


class OpenAICompatibleLLM:
    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
        timeout: float = 60.0,
    ) -> None:
        self.api_key = api_key or os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY")
        self.base_url = base_url or os.getenv("LLM_BASE_URL") or "https://api.openai.com/v1"
        self.model = model or os.getenv("LLM_MODEL") or "gpt-4o-mini"
        self.timeout = timeout
        if not self.api_key:
            raise LLMError("缺少 LLM_API_KEY / OPENAI_API_KEY")

    def complete(self, messages: list[dict]) -> str:
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise LLMError("请先安装 openai 包") from exc

        client = OpenAI(api_key=self.api_key, base_url=self.base_url, timeout=self.timeout)
        try:
            response = client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.2,
            )
        except Exception as exc:
            raise LLMError(f"LLM 调用失败: {exc}") from exc
        content = response.choices[0].message.content if response.choices else None
        if not content:
            raise LLMError("LLM 返回空内容")
        return content
