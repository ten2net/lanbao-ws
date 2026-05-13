"""Orchestrator 和 ReportStore 测试"""
import pytest
from datetime import datetime

from lanbao_ai_research.orchestrator import AgentOrchestrator
from lanbao_ai_research.report_store import ReportStore
from lanbao_ai_research.models import ResearchReport, ReportSummary


class MockDataClient:
    """Mock 数据客户端"""

    async def get_ohlcv(self, symbol, start, end, freq="daily"):
        import pandas as pd
        dates = pd.date_range(start, periods=10, freq="D")
        return pd.DataFrame({
            "close": [100 + i for i in range(10)],
            "volume": [1000000] * 10,
        }, index=dates)

    async def get_financial_data(self, symbol):
        return {"pe": 20, "pb": 3}

    async def save_report_metadata(self, **kwargs):
        return True


class TestAgentOrchestrator:
    """编排器测试"""

    @pytest.mark.asyncio
    async def test_run_stock_research(self, mock_llm):
        data_client = MockDataClient()
        orchestrator = AgentOrchestrator(mock_llm, data_client)

        result = await orchestrator.run_stock_research("600519")

        assert result.report_id.startswith("rpt_600519_")
        assert result.report_type == "stock_analysis"
        assert result.created_at != ""

    @pytest.mark.asyncio
    async def test_run_market_daily_research(self, mock_llm):
        data_client = MockDataClient()
        orchestrator = AgentOrchestrator(mock_llm, data_client)

        result = await orchestrator.run_market_daily_research(
            symbols=["600519"],
            report_id="rpt_test"
        )

        assert result.report_id == "rpt_test"
        assert result.report_type == "market_daily"
        assert result.summary.overall_verdict is not None


class TestReportStore:
    """报告存储测试"""

    def test_save_and_load(self, tmp_path, mock_llm):
        store = ReportStore(storage_path=str(tmp_path / "reports"))
        data_client = MockDataClient()

        report = ResearchReport(
            report_id="rpt_test",
            report_type="stock_analysis",
            created_at=datetime.now().isoformat(),
            summary=ReportSummary(
                overall_verdict="BUY",
                confidence=0.8,
                market_trend="上涨"
            )
        )

        filepath = store.save(report, data_client)
        assert filepath.endswith("rpt_test.md")

        loaded = store.load("rpt_test")
        assert loaded is not None
        assert "揽宝智能投研报告" in loaded
        assert "BUY" in loaded

    def test_to_markdown(self, tmp_path):
        store = ReportStore(storage_path=str(tmp_path))

        report = ResearchReport(
            report_id="rpt_test",
            report_type="market_daily",
            created_at="2024-01-01T00:00:00",
            summary=ReportSummary(
                overall_verdict="BUY",
                confidence=0.85,
                market_trend="大盘上涨"
            )
        )

        markdown = store._to_markdown(report)
        assert "# 揽宝智能投研报告" in markdown
        assert "BUY" in markdown
        assert "85%" in markdown
        assert "大盘上涨" in markdown
