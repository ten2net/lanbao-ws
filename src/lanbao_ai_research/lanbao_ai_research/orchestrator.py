"""Agent Orchestrator — 智能体调度中心"""
import asyncio
import time
from typing import List, Dict, Any, Optional
from datetime import datetime

from loguru import logger

from .models import (
    ResearchReport, AnalysisContext, AgentReport,
    FundamentalReport, TechnicalReport, SentimentReport,
)
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

        # 构建宏观分析数据：从实际获取的 OHLCV 中计算市场摘要
        market_summary = self._build_market_summary(stock_data_map)
        macro_context = AnalysisContext(
            market_data=market_summary
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

        # 阶段3：将各Agent独立分析结果合并到报告中，让用户能看到多智能体的独立观点
        self._merge_agent_reports(final_report, stock_reports)

        logger.info(f"市场日报分析完成: {report_id}, 耗时: {time.time() - start:.1f}s")
        return final_report

    def _merge_agent_reports(self, report: ResearchReport,
                             stock_reports: Dict[str, Dict[str, AgentReport]]):
        """将各Agent独立分析结果合并到最终报告中"""
        for stock_analysis in report.stock_analyses:
            symbol = stock_analysis.symbol
            if symbol not in stock_reports:
                continue
            agents = stock_reports[symbol]

            # 基本面分析
            fund = agents.get("fundamental")
            if fund and fund.success:
                try:
                    stock_analysis.fundamental = FundamentalReport(**fund.data)
                except Exception:
                    pass

            # 技术面分析
            tech = agents.get("technical")
            if tech and tech.success:
                try:
                    stock_analysis.technical = TechnicalReport(**tech.data)
                except Exception:
                    pass

            # 情绪面分析
            sent = agents.get("sentiment")
            if sent and sent.success:
                try:
                    stock_analysis.sentiment = SentimentReport(**sent.data)
                except Exception:
                    pass

    def _build_market_summary(self, stock_data_map: Dict[str, Any]) -> Dict[str, Any]:
        """从个股 OHLCV 中构建市场摘要，供宏观分析师使用"""
        summary = {
            "index": "沪深300",
            "analysis_date": datetime.now().strftime("%Y-%m-%d"),
            "symbols_count": len(stock_data_map),
            "valid_symbols_count": sum(1 for d in stock_data_map.values() if d and d.get("ohlcv") is not None),
            "stocks": [],
        }

        total_change_pct = 0.0
        valid_change_count = 0
        total_volume = 0

        for symbol, data in stock_data_map.items():
            if not data or data.get("ohlcv") is None:
                summary["stocks"].append({"symbol": symbol, "status": "数据缺失"})
                continue

            df = data["ohlcv"]
            if len(df) < 2:
                summary["stocks"].append({"symbol": symbol, "status": "数据不足"})
                continue

            latest = df.iloc[-1]
            prev = df.iloc[-2]
            change_pct = round((latest['close'] - prev['close']) / prev['close'] * 100, 2)
            total_change_pct += change_pct
            valid_change_count += 1
            total_volume += int(latest['volume']) if 'volume' in df.columns else 0

            # 计算20日均线
            ma20 = round(df['close'].rolling(20).mean().iloc[-1], 2) if len(df) >= 20 else None

            stock_info = {
                "symbol": symbol,
                "latest_close": round(latest['close'], 2),
                "prev_close": round(prev['close'], 2),
                "change_pct": change_pct,
                "volume": int(latest['volume']) if 'volume' in df.columns else None,
                "high_20d": round(df['high'].max(), 2) if 'high' in df.columns else None,
                "low_20d": round(df['low'].min(), 2) if 'low' in df.columns else None,
                "ma20": ma20,
                "above_ma20": bool(latest['close'] > ma20) if ma20 else None,
            }
            summary["stocks"].append(stock_info)

        if valid_change_count > 0:
            summary["avg_change_pct"] = round(total_change_pct / valid_change_count, 2)
            summary["market_sentiment"] = "上涨" if summary["avg_change_pct"] > 1 else "下跌" if summary["avg_change_pct"] < -1 else "震荡"
        else:
            summary["avg_change_pct"] = 0.0
            summary["market_sentiment"] = "数据不足"

        summary["total_volume"] = total_volume
        return summary

    async def _fetch_stock_data(self, symbol: str) -> Optional[Dict[str, Any]]:
        try:
            # 获取最近60天数据用于分析
            from datetime import timedelta
            end = datetime.now()
            start = end - timedelta(days=60)
            ohlcv = await self.data.get_ohlcv(
                symbol,
                start.strftime("%Y%m%d"),
                end.strftime("%Y%m%d"),
            )
            # 财务数据是可选的，服务不可用时不影响 OHLCV 分析
            try:
                financial = await self.data.get_financial_data(symbol)
            except Exception:
                financial = None
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
