"""LLM Provider 工厂"""
from .base import BaseLLMProvider, LLMConfig
from .deepseek import DeepSeekProvider


PROVIDER_REGISTRY = {
    "deepseek": DeepSeekProvider,
    "qwen": None,
    "openrouter": None,
}


def create_provider(config: LLMConfig) -> BaseLLMProvider:
    """创建 Provider 实例"""
    provider_class = PROVIDER_REGISTRY.get(config.provider)
    if provider_class is None:
        raise ValueError(f"不支持的 LLM Provider: {config.provider}")
    return provider_class(config)
