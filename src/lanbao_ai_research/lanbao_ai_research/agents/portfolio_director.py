"""投资总监智能体"""
import json
import time
from typing import Dict

from loguru import logger

from .base_agent import BaseAgent
from ..models import (
    AgentReport, AnalysisContext, ResearchReport, ReportSummary,
    StockAnalysis, StockSynthesis, PortfolioSuggestions
)


class PortfolioDirector(BaseAgent):
    """投资总监 — 综合四方报告，Bull/Bear 辩论，最终决策"""

    def __init__(self, llm_client):
        super().__init__("portfolio_director", llm_client, "portfolio_director.txt")

    async def analyze(self, context: AnalysisContext) -> AgentReport:
        """投资总监的分析方法（抽象方法实现）"""
        # PortfolioDirector 主要通过 synthesize 工作，analyze 作为占位实现
        return AgentReport(
            agent_name=self.name,
            success=True,
            data={"message": "PortfolioDirector 使用 synthesize 方法进行综合决策"}
        )

    async def synthesize(self, macro_report: AgentReport,
                        stock_reports: Dict[str, Dict[str, AgentReport]]) -> ResearchReport:
        """综合所有报告，生成最终投研报告"""
        start = time.time()

        try:
            macro_text = json.dumps(macro_report.data, ensure_ascii=False, indent=2) if macro_report.success else "宏观分析失败"

            stock_texts = []
            for symbol, reports in stock_reports.items():
                stock_info = {
                    "symbol": symbol,
                    "fundamental": reports.get("fundamental", {}).data if reports.get("fundamental") else {},
                    "technical": reports.get("technical", {}).data if reports.get("technical") else {},
                    "sentiment": reports.get("sentiment", {}).data if reports.get("sentiment") else {},
                }
                stock_texts.append(json.dumps(stock_info, ensure_ascii=False, indent=2))

            prompt = self._format_prompt(
                macro_report=macro_text,
                stock_reports="\n\n".join(stock_texts)
            )

            response = await self._call_llm(
                prompt,
                system="你是一位资深的投资总监，只输出 JSON 格式结果。",
                temperature=0.2
            )

            parsed = self._parse_json_response(response)

            if parsed:
                summary = ReportSummary(**parsed.get("summary", {}))

                stock_analyses = []
                for sa in parsed.get("stock_analyses", []):
                    stock_analyses.append(StockAnalysis(
                        symbol=sa["symbol"],
                        synthesis=StockSynthesis(**sa.get("synthesis", {}))
                    ))

                portfolio = PortfolioSuggestions(**parsed.get("portfolio_suggestions", {}))

                report = ResearchReport(
                    report_id="",
                    report_type="market_daily",
                    summary=summary,
                    macro_analysis=macro_report.data if macro_report.success else None,
                    stock_analyses=stock_analyses,
                    portfolio_suggestions=portfolio
                )
            else:
                report = ResearchReport(
                    report_id="",
                    report_type="market_daily",
                    summary=ReportSummary(raw_analysis=response[:500] if response else "解析失败")
                )

            return report
        except Exception as e:
            logger.error(f"投资总监综合失败: {e}")
            return ResearchReport(
                report_id="",
                report_type="market_daily",
                summary=ReportSummary(raw_analysis=f"综合失败: {str(e)}")
            )
