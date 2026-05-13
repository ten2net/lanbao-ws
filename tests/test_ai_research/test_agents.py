"""智能体测试"""
import pytest
import pandas as pd
from datetime import datetime, timedelta

from lanbao_ai_research.agents.macro_analyst import MacroAnalyst
from lanbao_ai_research.agents.fundamental_analyst import FundamentalAnalyst
from lanbao_ai_research.agents.technical_analyst import TechnicalAnalyst
from lanbao_ai_research.agents.sentiment_news_analyst import SentimentNewsAnalyst
from lanbao_ai_research.agents.portfolio_director import PortfolioDirector
from lanbao_ai_research.models import AnalysisContext


class TestMacroAnalyst:
    """宏观分析师测试"""

    @pytest.mark.asyncio
    async def test_analyze_returns_report(self, mock_llm):
        agent = MacroAnalyst(mock_llm)
        context = AnalysisContext(market_data={"index": "沪深300", "change": 0.02})
        result = await agent.analyze(context)

        assert result.success is True
        assert result.agent_name == "macro_analyst"
        assert "market_trend" in result.data
        assert result.data["market_trend"] == "UP"


class TestFundamentalAnalyst:
    """基本面分析师测试"""

    @pytest.mark.asyncio
    async def test_analyze_with_financial_data(self, mock_llm):
        agent = FundamentalAnalyst(mock_llm)
        context = AnalysisContext(
            symbol="600519",
            financial_data={"name": "贵州茅台", "pe": 30}
        )
        result = await agent.analyze(context)

        assert result.success is True
        assert result.data["verdict"] == "BUY"
        assert result.data["score"] == 80


class TestTechnicalAnalyst:
    """技术分析师测试"""

    def test_calculate_indicators_empty_data(self, mock_llm):
        agent = TechnicalAnalyst(mock_llm)
        result = agent._calculate_indicators(None)
        assert result == {}

    def test_calculate_indicators_with_data(self, mock_llm):
        agent = TechnicalAnalyst(mock_llm)
        dates = pd.date_range("2024-01-01", periods=30, freq="D")
        df = pd.DataFrame({
            "close": [100 + i * 0.5 for i in range(30)],
            "volume": [1000000] * 30,
        }, index=dates)

        result = agent._calculate_indicators(df)

        assert "rsi" in result
        assert "macd" in result
        assert "ma5" in result
        assert result["current_price"] == 114.5

    @pytest.mark.asyncio
    async def test_analyze(self, mock_llm):
        agent = TechnicalAnalyst(mock_llm)
        dates = pd.date_range("2024-01-01", periods=30, freq="D")
        df = pd.DataFrame({
            "close": [100 + i * 0.5 for i in range(30)],
            "volume": [1000000] * 30,
        }, index=dates)

        context = AnalysisContext(symbol="600519", market_data=df)
        result = await agent.analyze(context)

        assert result.success is True
        assert result.data["verdict"] == "BUY"


class TestSentimentNewsAnalyst:
    """情绪新闻分析师测试"""

    @pytest.mark.asyncio
    async def test_analyze(self, mock_llm):
        agent = SentimentNewsAnalyst(mock_llm, news_enabled=False)
        context = AnalysisContext(symbol="600519")
        result = await agent.analyze(context)

        assert result.success is True
        assert result.data["verdict"] == "BUY"

    @pytest.mark.asyncio
    async def test_fetch_news_disabled(self, mock_llm):
        agent = SentimentNewsAnalyst(mock_llm, news_enabled=False)
        news = await agent._fetch_news("600519")
        assert news == []


class TestPortfolioDirector:
    """投资总监测试"""

    @pytest.mark.asyncio
    async def test_synthesize(self, mock_llm):
        agent = PortfolioDirector(mock_llm)
        from lanbao_ai_research.models import AgentReport

        macro_report = AgentReport(
            agent_name="macro",
            success=True,
            data={"market_trend": "UP"}
        )

        stock_reports = {
            "600519": {
                "fundamental": AgentReport(agent_name="fundamental", success=True, data={"verdict": "BUY", "score": 80}),
                "technical": AgentReport(agent_name="technical", success=True, data={"verdict": "BUY", "score": 75}),
                "sentiment": AgentReport(agent_name="sentiment", success=True, data={"verdict": "BUY", "score": 70}),
            }
        }

        result = await agent.synthesize(macro_report, stock_reports)

        assert result.report_id == ""
        assert result.summary.overall_verdict == "BUY"
        assert result.summary.confidence == 0.8
        assert len(result.stock_analyses) >= 1
