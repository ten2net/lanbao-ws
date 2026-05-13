"""DeepSeek LLM Provider"""
import asyncio
import json
from typing import AsyncGenerator, Optional

import httpx
from loguru import logger

from .base import BaseLLMProvider, LLMConfig, LLMResponse


class DeepSeekProvider(BaseLLMProvider):
    """DeepSeek API Provider"""

    DEFAULT_BASE_URL = "https://api.deepseek.com/v1"

    def __init__(self, config: LLMConfig):
        super().__init__(config)
        self.base_url = config.base_url or self.DEFAULT_BASE_URL
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            headers={"Authorization": f"Bearer {config.api_key}"},
            timeout=config.timeout,
        )

    async def complete(self, prompt: str, system: Optional[str] = None) -> LLMResponse:
        """非流式完成"""
        messages = self._build_messages(prompt, system)

        for attempt in range(self.config.max_retries):
            try:
                response = await self.client.post(
                    "/chat/completions",
                    json={
                        "model": self.config.model,
                        "messages": messages,
                        "temperature": self.config.temperature,
                        "max_tokens": self.config.max_tokens,
                    }
                )
                response.raise_for_status()
                data = await response.json()

                choice = data["choices"][0]
                return LLMResponse(
                    content=choice["message"]["content"],
                    usage=data.get("usage", {}),
                    model=data.get("model", ""),
                    finish_reason=choice.get("finish_reason", ""),
                )
            except Exception as e:
                logger.warning(f"DeepSeek API 调用失败 (attempt {attempt + 1}): {e}")
                if attempt < self.config.max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
                else:
                    raise

        raise RuntimeError("DeepSeek API 调用全部失败")

    async def complete_stream(self, prompt: str, system: Optional[str] = None) -> AsyncGenerator[str, None]:
        """流式完成"""
        messages = self._build_messages(prompt, system)

        async with self.client.stream(
            "POST",
            "/chat/completions",
            json={
                "model": self.config.model,
                "messages": messages,
                "temperature": self.config.temperature,
                "max_tokens": self.config.max_tokens,
                "stream": True,
            }
        ) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data_str = line[6:]
                    if data_str == "[DONE]":
                        break
                    try:
                        data = json.loads(data_str)
                        delta = data["choices"][0]["delta"]
                        if "content" in delta:
                            yield delta["content"]
                    except (json.JSONDecodeError, KeyError):
                        continue
