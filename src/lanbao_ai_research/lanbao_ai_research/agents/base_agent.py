"""智能体基类"""
import json
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from pathlib import Path

from loguru import logger

from ..models import AgentReport, AnalysisContext
from ..llm.client import LLMClient


class BaseAgent(ABC):
    """投研智能体基类"""

    def __init__(self, name: str, llm_client: LLMClient,
                 prompt_file: Optional[str] = None):
        self.name = name
        self.llm = llm_client
        self.prompt_template = self._load_prompt(prompt_file) if prompt_file else ""

    def _load_prompt(self, prompt_file: str) -> str:
        """加载 Prompt 模板"""
        prompt_path = Path(__file__).parent.parent / "llm" / "prompts" / prompt_file
        if prompt_path.exists():
            return prompt_path.read_text(encoding='utf-8')
        logger.warning(f"Prompt 文件不存在: {prompt_path}")
        return ""

    @abstractmethod
    async def analyze(self, context: AnalysisContext) -> AgentReport:
        """执行分析

        Args:
            context: 分析上下文，包含所需数据

        Returns:
            AgentReport: 结构化分析报告
        """
        pass

    def _format_prompt(self, **kwargs) -> str:
        """格式化 Prompt 模板（使用 replace 而非 format，避免 JSON 代码块被误解析）"""
        result = self.prompt_template
        for key, value in kwargs.items():
            result = result.replace(f"{{{key}}}", str(value))
        return result

    async def _call_llm(self, prompt: str, system: Optional[str] = None,
                        temperature: Optional[float] = None) -> str:
        """调用 LLM，自动处理重试"""
        return await self.llm.complete(prompt, system, temperature)

    def _parse_json_response(self, text: str) -> Optional[Dict[str, Any]]:
        """从 LLM 响应中提取 JSON"""
        # 尝试直接解析
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # 尝试从 markdown code block 中提取
        import re
        json_match = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass

        # 尝试查找 { ... } 结构
        json_match = re.search(r'\{.*\}', text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(0))
            except json.JSONDecodeError:
                pass

        logger.warning(f"无法从响应中提取 JSON: {text[:200]}...")
        return None
