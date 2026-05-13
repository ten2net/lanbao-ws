"""Agent Orchestrator — 智能体调度中心"""
import asyncio
import time
from typing import List, Dict, Any, Optional
from datetime import datetime

from loguru import logger

from .models import ResearchReport, AnalysisContext, AgentReport
from .agents.macro_analyst import MacroAnalyst
from .agents.fundamental_analyst import FundamentalAnalyst
from .agents.technical_analyst import TechnicalAnalyst
from .agents.sentiment_news_analyst import SentimentNewsAnalyst
from .agents.portfolio_director import PortfolioDirector
from .llm.client import LLMClient
from .data_client.ros2_data_client import ROS2DataClient


class AgentOrchestrator:
    """智能体编排器"""

    def __init__(self, llm_client: LLMClient, data_client: ROS2DataClient):
        self.llm = llm_client
        self.data = data_client

        self.macro_analyst = MacroAnalyst(llm_client)
        self.fundamental_analyst = FundamentalAnalyst(llm_client)
        self.technical_analyst = TechnicalAnalyst(llm_client)
        self.sentiment_news_analyst = SentimentNewsAnalyst(llm_client)
        self.portfolio_director = PortfolioDirector(llm_client)

    async def run_market_daily_research(self, symbols: List[str],
                                        report_id: str = None) -> ResearchReport:
        if report_id is None:
            report_id = f"rpt_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        logger.info(f"开始市场日报分析: {report_id}, 标的: {symbols}")
        start = time.time()

        # 阶段1：并行分析
        logger.info("阶段1: 并行启动分析师...")

        # 获取数据
        data_tasks = [self._fetch_stock_data(s) for s in symbols]
        stock_data_list = await asyncio.gather(*data_tasks, return_exceptions=True)
        stock_data_map = {}
        for i, symbol in enumerate(symbols):
            result = stock_data_list[i]
            stock_data_map[symbol] = None if isinstance(result, Exception) else result

        # 宏观分析
        macro_context = AnalysisContext(
            market_data={"symbols": symbols, "data_map": {s: "ok" if d else "fail" for s, d in stock_data_map.items()}}
        )
        macro_task = self.macro_analyst.analyze(macro_context)

        # 个股分析
        stock_analysis_tasks = {}
        for symbol in symbols:
            data = stock_data_map.get(symbol)
            if data:
                context = AnalysisContext(
                    symbol=symbol,
                    market_data=data.get("ohlcv"),
                    financial_data=data.get("financial"),
                )
                stock_analysis_tasks[symbol] = {
                    "fundamental": self.fundamental_analyst.analyze(context),
                    "technical": self.technical_analyst.analyze(context),
                    "sentiment": self.sentiment_news_analyst.analyze(context),
                }

        macro_report = await macro_task

        stock_reports = {}
        for symbol, tasks in stock_analysis_tasks.items():
            results = await asyncio.gather(
                tasks["fundamental"], tasks["technical"], tasks["sentiment"],
                return_exceptions=True
            )
            stock_reports[symbol] = {
                "fundamental": results[0] if not isinstance(results[0], Exception) else AgentReport(agent_name="fundamental", success=False, error_message=str(results[0])),
                "technical": results[1] if not isinstance(results[1], Exception) else AgentReport(agent_name="technical", success=False, error_message=str(results[1])),
                "sentiment": results[2] if not isinstance(results[2], Exception) else AgentReport(agent_name="sentiment", success=False, error_message=str(results[2])),
            }

        # 阶段2：投资总监综合
        logger.info("阶段2: 投资总监综合...")
        final_report = await self.portfolio_director.synthesize(macro_report, stock_reports)
        final_report.report_id = report_id
        final_report.report_type = "market_daily"
        final_report.created_at = datetime.now().isoformat()

        logger.info(f"市场日报分析完成: {report_id}, 耗时: {time.time() - start:.1f}s")
        return final_report

    async def _fetch_stock_data(self, symbol: str) -> Optional[Dict[str, Any]]:
        try:
            ohlcv = await self.data.get_ohlcv(symbol, "20250101", datetime.now().strftime("%Y%m%d"))
            financial = await self.data.get_financial_data(symbol)
            return {"ohlcv": ohlcv, "financial": financial}
        except Exception as e:
            logger.warning(f"获取 {symbol} 数据失败: {e}")
            return None

    async def run_stock_research(self, symbol: str, report_id: str = None) -> ResearchReport:
        if report_id is None:
            report_id = f"rpt_{symbol}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        logger.info(f"开始个股分析: {symbol}")

        data = await self._fetch_stock_data(symbol)
        if not data:
            return ResearchReport(report_id=report_id, report_type="stock_analysis", created_at=datetime.now().isoformat())

        context = AnalysisContext(symbol=symbol, market_data=data.get("ohlcv"), financial_data=data.get("financial"))

        fund_report, tech_report, sent_report = await asyncio.gather(
            self.fundamental_analyst.analyze(context),
            self.technical_analyst.analyze(context),
            self.sentiment_news_analyst.analyze(context),
            return_exceptions=True
        )

        stock_reports = {
            symbol: {
                "fundamental": fund_report if not isinstance(fund_report, Exception) else AgentReport(agent_name="fundamental", success=False),
                "technical": tech_report if not isinstance(tech_report, Exception) else AgentReport(agent_name="technical", success=False),
                "sentiment": sent_report if not isinstance(sent_report, Exception) else AgentReport(agent_name="sentiment", success=False),
            }
        }

        final_report = await self.portfolio_director.synthesize(
            AgentReport(agent_name="macro", success=True, data={}), stock_reports
        )
        final_report.report_id = report_id
        final_report.report_type = "stock_analysis"
        final_report.created_at = datetime.now().isoformat()
        return final_report
