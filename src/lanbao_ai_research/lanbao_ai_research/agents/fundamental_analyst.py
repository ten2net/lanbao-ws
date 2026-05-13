"""基本面分析师智能体"""
import json
import time

from loguru import logger

from .base_agent import BaseAgent
from ..models import AgentReport, AnalysisContext, FundamentalReport


class FundamentalAnalyst(BaseAgent):
    """基本面分析师 — 分析财务健康度、估值、行业地位"""

    def __init__(self, llm_client):
        super().__init__("fundamental_analyst", llm_client, "fundamental_analyst.txt")

    async def analyze(self, context: AnalysisContext) -> AgentReport:
        start = time.time()

        try:
            symbol = context.symbol or "UNKNOWN"
            financial = context.financial_data or {}

            prompt = self.prompt_template.format(
                symbol=symbol,
                name=financial.get("name", symbol),
                financial_data=json.dumps(financial, ensure_ascii=False, indent=2)
            )

            response = await self._call_llm(
                prompt,
                system="你是一位资深的基本面分析师，只输出 JSON 格式结果。",
                temperature=0.2
            )

            parsed = self._parse_json_response(response)
            report = FundamentalReport(**parsed) if parsed else FundamentalReport()

            return AgentReport(
                agent_name=self.name,
                success=parsed is not None,
                data=report.model_dump(),
                raw_text=response,
                duration_seconds=time.time() - start
            )
        except Exception as e:
            logger.error(f"基本面分析失败 [{context.symbol}]: {e}")
            return AgentReport(
                agent_name=self.name,
                success=False,
                error_message=str(e),
                data=FundamentalReport().model_dump(),
                duration_seconds=time.time() - start
            )
