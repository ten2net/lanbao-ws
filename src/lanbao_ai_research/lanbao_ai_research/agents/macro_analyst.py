"""宏观分析师智能体"""
import json

from loguru import logger

from .base_agent import BaseAgent
from ..models import AgentReport, AnalysisContext, MacroReport


class MacroAnalyst(BaseAgent):
    """宏观分析师 — 分析大盘走势、板块轮动、政策环境"""

    def __init__(self, llm_client):
        super().__init__("macro_analyst", llm_client, "macro_analyst.txt")

    async def analyze(self, context: AnalysisContext) -> AgentReport:
        import time
        start = time.time()

        try:
            market_data = context.market_data or {}
            data_text = json.dumps(market_data, ensure_ascii=False, indent=2, default=str)
            prompt = self._format_prompt(data=data_text)

            response = await self._call_llm(
                prompt,
                system="你是一位资深的宏观分析师，只输出 JSON 格式结果。",
                temperature=0.3
            )

            parsed = self._parse_json_response(response)
            report = MacroReport(**parsed) if parsed else MacroReport(raw_analysis=response[:500] if response else "解析失败")

            return AgentReport(
                agent_name=self.name,
                success=True,
                data=report.model_dump(),
                raw_text=response,
                duration_seconds=time.time() - start
            )
        except Exception as e:
            logger.error(f"宏观分析失败: {e}")
            return AgentReport(
                agent_name=self.name,
                success=False,
                error_message=str(e),
                data=MacroReport().model_dump(),
                duration_seconds=time.time() - start
            )
