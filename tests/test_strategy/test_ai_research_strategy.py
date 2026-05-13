"""AIResearchStrategy 测试"""
import pytest
import pandas as pd
from datetime import datetime, timedelta

from lanbao_strategy.ai_research_strategy import AIResearchStrategy
from lanbao_strategy.strategy_template import Signal


@pytest.fixture
def sample_data():
    dates = pd.date_range("2024-01-01", periods=30, freq="D")
    return pd.DataFrame({
        "close": [100 + i * 0.5 for i in range(30)],
        "volume": [1000000] * 30,
        "symbol": ["600519"] * 30,
    }, index=dates)


class TestVerdictMapping:
    """评级映射测试"""

    def test_strong_buy_mapping(self, sample_data):
        strategy = AIResearchStrategy("ai_1", symbol="600519")
        strategy.set_report_provider(lambda s: {
            "created_at": datetime.now().isoformat(),
            "stock_analyses": [{
                "symbol": "600519",
                "synthesis": {"verdict": "STRONG_BUY", "score": 90}
            }],
            "summary": {"confidence": 0.9}
        })

        signals = strategy.generate_signals(sample_data)
        assert len(signals) == 1
        assert signals[0].action == "BUY"
        assert signals[0].strength > 0.8  # 1.0 * 0.9 * 0.9 ≈ 0.81
        assert "STRONG_BUY" in signals[0].reason

    def test_buy_mapping(self, sample_data):
        strategy = AIResearchStrategy("ai_1", symbol="600519")
        strategy.set_report_provider(lambda s: {
            "created_at": datetime.now().isoformat(),
            "stock_analyses": [{
                "symbol": "600519",
                "synthesis": {"verdict": "BUY", "score": 75}
            }],
            "summary": {"confidence": 0.8}
        })

        signals = strategy.generate_signals(sample_data)
        assert len(signals) == 1
        assert signals[0].action == "BUY"
        # strength = 0.7 * 0.8 * 0.75 = 0.42
        assert abs(signals[0].strength - 0.42) < 0.01

    def test_hold_mapping(self, sample_data):
        strategy = AIResearchStrategy("ai_1", symbol="600519")
        strategy.set_report_provider(lambda s: {
            "created_at": datetime.now().isoformat(),
            "stock_analyses": [{
                "symbol": "600519",
                "synthesis": {"verdict": "HOLD", "score": 50}
            }],
            "summary": {"confidence": 0.5}
        })

        signals = strategy.generate_signals(sample_data)
        assert len(signals) == 1
        assert signals[0].action == "HOLD"
        assert signals[0].strength == 0.0

    def test_sell_mapping(self, sample_data):
        strategy = AIResearchStrategy("ai_1", symbol="600519")
        strategy.set_report_provider(lambda s: {
            "created_at": datetime.now().isoformat(),
            "stock_analyses": [{
                "symbol": "600519",
                "synthesis": {"verdict": "SELL", "score": 40}
            }],
            "summary": {"confidence": 0.7}
        })

        signals = strategy.generate_signals(sample_data)
        assert len(signals) == 1
        assert signals[0].action == "SELL"

    def test_strong_sell_mapping(self, sample_data):
        strategy = AIResearchStrategy("ai_1", symbol="600519")
        strategy.set_report_provider(lambda s: {
            "created_at": datetime.now().isoformat(),
            "stock_analyses": [{
                "symbol": "600519",
                "synthesis": {"verdict": "STRONG_SELL", "score": 20}
            }],
            "summary": {"confidence": 0.9}
        })

        signals = strategy.generate_signals(sample_data)
        assert len(signals) == 1
        assert signals[0].action == "SELL"
        assert signals[0].strength > 0.15  # 1.0 * 0.9 * 0.2 = 0.18


class TestStrengthCalculation:
    """信号强度计算测试"""

    def test_strength_formula(self, sample_data):
        strategy = AIResearchStrategy("ai_1", symbol="600519")
        strategy.set_report_provider(lambda s: {
            "created_at": datetime.now().isoformat(),
            "stock_analyses": [{
                "symbol": "600519",
                "synthesis": {"verdict": "BUY", "score": 80}
            }],
            "summary": {"confidence": 0.8}
        })

        signals = strategy.generate_signals(sample_data)
        # strength = base(0.7) * confidence(0.8) * score_ratio(0.8) = 0.448
        expected = 0.7 * 0.8 * 0.8
        assert abs(signals[0].strength - expected) < 0.001
        assert signals[0].params["base_strength"] == 0.7
        assert signals[0].params["confidence"] == 0.8
        assert signals[0].params["score"] == 80

    def test_strength_capped_at_1(self, sample_data):
        strategy = AIResearchStrategy("ai_1", symbol="600519")
        strategy.set_report_provider(lambda s: {
            "created_at": datetime.now().isoformat(),
            "stock_analyses": [{
                "symbol": "600519",
                "synthesis": {"verdict": "STRONG_BUY", "score": 100}
            }],
            "summary": {"confidence": 1.0}
        })

        signals = strategy.generate_signals(sample_data)
        # strength = 1.0 * 1.0 * 1.0 = 1.0，不应超过 1.0
        assert signals[0].strength == pytest.approx(1.0, abs=0.001)


class TestFallbackMechanisms:
    """降级机制测试"""

    def test_no_provider_fallback(self, sample_data):
        strategy = AIResearchStrategy("ai_1", symbol="600519")
        # 不设置 provider
        signals = strategy.generate_signals(sample_data)
        assert len(signals) == 1
        assert signals[0].action == "HOLD"
        assert signals[0].params["fallback"] is True
        assert "获取失败" in signals[0].reason

    def test_provider_returns_none(self, sample_data):
        strategy = AIResearchStrategy("ai_1", symbol="600519")
        strategy.set_report_provider(lambda s: None)
        signals = strategy.generate_signals(sample_data)
        assert len(signals) == 1
        assert signals[0].action == "HOLD"
        assert signals[0].params["fallback"] is True

    def test_provider_raises_exception(self, sample_data):
        strategy = AIResearchStrategy("ai_1", symbol="600519")
        strategy.set_report_provider(lambda s: (_ for _ in ()).throw(Exception("timeout")))
        signals = strategy.generate_signals(sample_data)
        assert len(signals) == 1
        assert signals[0].action == "HOLD"

    def test_symbol_not_in_report(self, sample_data):
        strategy = AIResearchStrategy("ai_1", symbol="600519")
        strategy.set_report_provider(lambda s: {
            "created_at": datetime.now().isoformat(),
            "stock_analyses": [{
                "symbol": "000001",  # 不同股票
                "synthesis": {"verdict": "BUY", "score": 80}
            }],
            "summary": {"overall_verdict": "HOLD", "confidence": 0.5}
        })
        signals = strategy.generate_signals(sample_data)
        # fallback 到 summary 的整体评级
        assert len(signals) == 1
        assert signals[0].action == "HOLD"


class TestReportExpiry:
    """报告过期衰减测试"""

    def test_fresh_report_no_decay(self, sample_data):
        strategy = AIResearchStrategy("ai_1", symbol="600519", expiry_hours=24)
        strategy.set_report_provider(lambda s: {
            "created_at": datetime.now().isoformat(),
            "stock_analyses": [{
                "symbol": "600519",
                "synthesis": {"verdict": "BUY", "score": 80}
            }],
            "summary": {"confidence": 0.8}
        })

        signals = strategy.generate_signals(sample_data)
        assert signals[0].params["decay_factor"] == 1.0

    def test_expired_report_full_decay(self, sample_data):
        strategy = AIResearchStrategy("ai_1", symbol="600519", expiry_hours=1)
        old_time = (datetime.now() - timedelta(hours=2)).isoformat()
        strategy.set_report_provider(lambda s: {
            "created_at": old_time,
            "stock_analyses": [{
                "symbol": "600519",
                "synthesis": {"verdict": "BUY", "score": 80}
            }],
            "summary": {"confidence": 0.8}
        })

        signals = strategy.generate_signals(sample_data)
        # 超过 1 小时，完全过期，衰减因子为 0
        assert signals[0].params["decay_factor"] == 0.0
        assert signals[0].strength == 0.0
        assert "衰减" in signals[0].reason

    def test_partial_decay(self, sample_data):
        strategy = AIResearchStrategy("ai_1", symbol="600519", expiry_hours=24)
        # 12 小时前的报告，应衰减 50%
        old_time = (datetime.now() - timedelta(hours=12)).strftime("%Y-%m-%dT%H:%M:%S")
        strategy.set_report_provider(lambda s: {
            "created_at": old_time,
            "stock_analyses": [{
                "symbol": "600519",
                "synthesis": {"verdict": "BUY", "score": 80}
            }],
            "summary": {"confidence": 0.8}
        })

        signals = strategy.generate_signals(sample_data)
        # decay ≈ 0.5
        assert 0.4 < signals[0].params["decay_factor"] < 0.6


class TestRefreshInterval:
    """刷新间隔测试"""

    def test_refresh_every_k_lines(self, sample_data):
        strategy = AIResearchStrategy("ai_1", symbol="600519", refresh_interval=3)
        call_count = 0

        def provider(s):
            nonlocal call_count
            call_count += 1
            return {
                "created_at": datetime.now().isoformat(),
                "stock_analyses": [{
                    "symbol": "600519",
                    "synthesis": {"verdict": "HOLD", "score": 50}
                }],
                "summary": {"confidence": 0.5}
            }

        strategy.set_report_provider(provider)

        # 调用 5 次，refresh_interval=3，应触发 2 次刷新（第 1, 4 次）
        for _ in range(5):
            strategy.generate_signals(sample_data)

        assert call_count == 2


class TestAggregateVerdicts:
    """多维度评级聚合测试"""

    def test_aggregate_verdicts_strong_buy(self, sample_data):
        strategy = AIResearchStrategy("ai_1", symbol="600519")
        strategy.set_report_provider(lambda s: {
            "created_at": datetime.now().isoformat(),
            "stock_analyses": [{
                "symbol": "600519",
                "fundamental": {"verdict": "STRONG_BUY", "score": 90},
                "technical": {"verdict": "BUY", "score": 80},
                "sentiment": {"verdict": "BUY", "score": 75},
            }],
            "summary": {"confidence": 0.8}
        })

        signals = strategy.generate_signals(sample_data)
        # 平均得分 (2+1+1)/3=1.33 → BUY（无synthesis时聚合）
        # 注意：如果有 synthesis 优先用 synthesis，这里测试无 synthesis 的情况
        # 实际上上面的结构没有 synthesis，所以会用聚合
        assert len(signals) == 1

    def test_aggregate_from_summary(self, sample_data):
        """无个股分析时，使用 summary 的整体评级"""
        strategy = AIResearchStrategy("ai_1", symbol="600519")
        strategy.set_report_provider(lambda s: {
            "created_at": datetime.now().isoformat(),
            "stock_analyses": [],
            "summary": {"overall_verdict": "BUY", "confidence": 0.7}
        })

        signals = strategy.generate_signals(sample_data)
        assert signals[0].action == "BUY"


class TestValidation:
    """验证测试"""

    def test_valid_config(self):
        strategy = AIResearchStrategy("ai_1", symbol="600519")
        assert strategy.validate() is True

    def test_missing_symbol(self):
        strategy = AIResearchStrategy("ai_1", symbol="")
        assert strategy.validate() is False

    def test_invalid_refresh_interval(self):
        strategy = AIResearchStrategy("ai_1", symbol="600519", refresh_interval=0)
        assert strategy.validate() is False

    def test_invalid_expiry_hours(self):
        strategy = AIResearchStrategy("ai_1", symbol="600519", expiry_hours=-1)
        assert strategy.validate() is False


class TestAnalyze:
    """analyze 方法测试"""

    def test_analyze_with_report(self, sample_data):
        strategy = AIResearchStrategy("ai_1", symbol="600519")
        strategy.set_report_provider(lambda s: {
            "created_at": datetime.now().isoformat(),
            "stock_analyses": [{
                "symbol": "600519",
                "synthesis": {"verdict": "BUY", "score": 80}
            }],
            "summary": {"confidence": 0.8}
        })

        result = strategy.analyze(sample_data)
        assert result["has_report"] is True
        assert result["verdict"] == "BUY"
        assert result["confidence"] == 0.8
        assert result["score"] == 80

    def test_analyze_without_report(self, sample_data):
        strategy = AIResearchStrategy("ai_1", symbol="600519")
        result = strategy.analyze(sample_data)
        assert result["has_report"] is False
        assert result["error"] == "无法获取投研报告"


class TestPydanticModelSupport:
    """Pydantic 模型输入测试"""

    def test_pydantic_report_input(self, sample_data):
        """测试接收 Pydantic ResearchReport 模型"""
        try:
            from lanbao_ai_research.models import ResearchReport, ReportSummary, StockAnalysis, StockSynthesis

            report = ResearchReport(
                report_id="rpt_test",
                summary=ReportSummary(overall_verdict="BUY", confidence=0.8),
                stock_analyses=[
                    StockAnalysis(
                        symbol="600519",
                        synthesis=StockSynthesis(verdict="BUY", score=80)
                    )
                ]
            )

            strategy = AIResearchStrategy("ai_1", symbol="600519")
            strategy.set_report_provider(lambda s: report)

            signals = strategy.generate_signals(sample_data)
            assert signals[0].action == "BUY"
            assert signals[0].params["score"] == 80
        except ImportError:
            pytest.skip("lanbao_ai_research 未安装")
