"""统一 LLM 客户端"""
import time
from typing import Optional, Dict, Any
from dataclasses import dataclass

from loguru import logger

from .providers.base import LLMConfig
from .providers.factory import create_provider


@dataclass
class UsageStats:
    """Token 使用统计"""
    total_requests: int = 0
    total_tokens: int = 0
    total_prompt_tokens: int = 0
    total_completion_tokens: int = 0
    failed_requests: int = 0


class LLMClient:
    """统一 LLM 客户端

    功能：
    - 支持多 Provider（DeepSeek、Qwen 等）
    - 自动重试
    - Token 用量统计
    - 降级策略
    """

    def __init__(self, config: LLMConfig):
        self.config = config
        self.provider = create_provider(config)
        self.stats = UsageStats()

    async def complete(self, prompt: str, system: Optional[str] = None,
                       temperature: Optional[float] = None) -> str:
        """完成调用，返回文本内容"""
        start = time.time()

        try:
            # 临时覆盖 temperature
            original_temp = self.provider.config.temperature
            if temperature is not None:
                self.provider.config.temperature = temperature

            response = await self.provider.complete(prompt, system)

            # 恢复 temperature
            self.provider.config.temperature = original_temp

            # 统计
            self.stats.total_requests += 1
            usage = response.usage or {}
            self.stats.total_tokens += usage.get("total_tokens", 0)
            self.stats.total_prompt_tokens += usage.get("prompt_tokens", 0)
            self.stats.total_completion_tokens += usage.get("completion_tokens", 0)

            duration = time.time() - start
            logger.info(f"LLM 调用完成: {duration:.1f}s, tokens: {usage.get('total_tokens', 0)}")

            return response.content

        except Exception as e:
            self.stats.failed_requests += 1
            logger.error(f"LLM 调用失败: {e}")
            raise

    async def complete_with_fallback(self, prompt: str, system: Optional[str] = None,
                                     fallback_configs: list = None) -> str:
        """带降级的完成调用"""
        try:
            return await self.complete(prompt, system)
        except Exception as e:
            logger.warning(f"主 LLM 失败，尝试降级: {e}")

            if fallback_configs:
                for fallback_config in fallback_configs:
                    try:
                        fallback_client = LLMClient(fallback_config)
                        return await fallback_client.complete(prompt, system)
                    except Exception as e2:
                        logger.warning(f"降级 LLM 也失败: {e2}")
                        continue

            raise

    def get_stats(self) -> Dict[str, Any]:
        """获取使用统计"""
        return {
            "total_requests": self.stats.total_requests,
            "total_tokens": self.stats.total_tokens,
            "failed_requests": self.stats.failed_requests,
            "avg_tokens_per_request": (
                self.stats.total_tokens / max(self.stats.total_requests, 1)
            ),
        }
