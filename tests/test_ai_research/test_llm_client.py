"""LLM Client 测试"""
import pytest
from unittest.mock import AsyncMock

from lanbao_ai_research.llm.providers.base import LLMConfig
from lanbao_ai_research.llm.providers.deepseek import DeepSeekProvider
from lanbao_ai_research.llm.providers.factory import create_provider


class TestDeepSeekProvider:
    """DeepSeek Provider 测试"""

    @pytest.fixture
    def config(self):
        return LLMConfig(
            provider="deepseek",
            model="deepseek-chat",
            api_key="test-key",
            temperature=0.3,
            max_tokens=100,
        )

    @pytest.fixture
    def provider(self, config):
        return DeepSeekProvider(config)

    @pytest.mark.asyncio
    async def test_complete_success(self, provider):
        """测试成功调用"""
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json = AsyncMock(return_value={
            "choices": [{"message": {"content": "测试回答"}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
            "model": "deepseek-chat"
        })
        mock_response.raise_for_status = AsyncMock()

        provider.client.post = AsyncMock(return_value=mock_response)

        result = await provider.complete("测试问题")
        assert result.content == "测试回答"
        assert result.usage["total_tokens"] == 15

    @pytest.mark.asyncio
    async def test_complete_with_system(self, provider):
        """测试带 system message 的调用"""
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json = AsyncMock(return_value={
            "choices": [{"message": {"content": "带系统的回答"}, "finish_reason": "stop"}],
            "usage": {},
            "model": "deepseek-chat"
        })
        mock_response.raise_for_status = AsyncMock()

        provider.client.post = AsyncMock(return_value=mock_response)

        result = await provider.complete("测试问题", system="你是一个分析师")
        assert result.content == "带系统的回答"


class TestProviderFactory:
    """Provider 工厂测试"""

    def test_create_deepseek(self):
        """测试创建 DeepSeek Provider"""
        config = LLMConfig(provider="deepseek", api_key="test")
        provider = create_provider(config)
        assert isinstance(provider, DeepSeekProvider)

    def test_create_unsupported(self):
        """测试不支持的 Provider"""
        config = LLMConfig(provider="unknown")
        with pytest.raises(ValueError):
            create_provider(config)
