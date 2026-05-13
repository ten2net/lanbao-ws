"""LLM Provider 基类"""
from abc import ABC, abstractmethod
from typing import AsyncGenerator, Optional, Dict, Any
from dataclasses import dataclass


@dataclass
class LLMResponse:
    """LLM 响应"""
    content: str
    usage: Dict[str, int] = None
    model: str = ""
    finish_reason: str = ""

    def __post_init__(self):
        if self.usage is None:
            self.usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}


@dataclass
class LLMConfig:
    """LLM 配置"""
    provider: str = "deepseek"
    model: str = "deepseek-chat"
    api_key: str = ""
    base_url: str = ""
    temperature: float = 0.3
    max_tokens: int = 4096
    timeout: float = 120.0
    max_retries: int = 3


class BaseLLMProvider(ABC):
    """LLM Provider 抽象基类"""

    def __init__(self, config: LLMConfig):
        self.config = config

    @abstractmethod
    async def complete(self, prompt: str, system: Optional[str] = None) -> LLMResponse:
        """非流式完成"""
        pass

    @abstractmethod
    async def complete_stream(self, prompt: str, system: Optional[str] = None) -> AsyncGenerator[str, None]:
        """流式完成"""
        pass

    def _build_messages(self, prompt: str, system: Optional[str] = None) -> list:
        """构建消息列表"""
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        return messages
