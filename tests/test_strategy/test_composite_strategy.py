"""CompositeStrategy 测试"""
import pytest
import pandas as pd
from datetime import datetime

from lanbao_strategy.strategy_template import Signal, MovingAverageCrossStrategy, RSIStrategy
from lanbao_strategy.composite_strategy import CompositeStrategy, SubStrategyConfig


@pytest.fixture
def sample_data():
    """生成测试用的市场数据"""
    dates = pd.date_range("2024-01-01", periods=30, freq="D")
    return pd.DataFrame({
        "close": [100 + i * 0.5 for i in range(30)],
        "volume": [1000000] * 30,
        "symbol": ["600519"] * 30,
    }, index=dates)


@pytest.fixture
def ma_strategy():
    return MovingAverageCrossStrategy("ma_test", fast_period=5, slow_period=20)


@pytest.fixture
def rsi_strategy():
    return RSIStrategy("rsi_test", period=14, oversold=30, overbought=70)


class TestCompositeStrategyInit:
    """初始化测试"""

    def test_default_init(self):
        strategy = CompositeStrategy("comp_1", "测试组合")
        assert strategy.strategy_id == "comp_1"
        assert strategy.voting_mode == "weighted_sum"
        assert strategy.sub_strategies == []
        assert strategy.validate() is False  # 无子策略，验证失败

    def test_init_with_sub_strategies(self, ma_strategy, rsi_strategy):
        strategy = CompositeStrategy(
            "comp_2",
            sub_strategies=[
                {"strategy": ma_strategy, "weight": 0.6},
                {"strategy": rsi_strategy, "weight": 0.4},
            ],
        )
        assert len(strategy.sub_strategies) == 2
        assert strategy.validate() is True

    def test_init_with_dict_config(self, ma_strategy):
        strategy = CompositeStrategy(
            "comp_3",
            sub_strategies=[{"strategy": ma_strategy, "weight": 1.0}],
            voting_mode="majority",
            threshold_buy=0.15,
            threshold_sell=-0.15,
            min_confidence=0.6,
        )
        assert strategy.voting_mode == "majority"
        assert strategy.validate() is True


class TestAddRemoveSubStrategy:
    """添加/移除子策略测试"""

    def test_add_sub_strategy(self):
        comp = CompositeStrategy("comp")
        ma = MovingAverageCrossStrategy("ma_1")
        comp.add_sub_strategy(ma, weight=0.5)

        assert len(comp.sub_strategies) == 1
        assert comp.sub_strategies[0].weight == 0.5

    def test_remove_sub_strategy(self):
        comp = CompositeStrategy("comp")
        ma = MovingAverageCrossStrategy("ma_1")
        comp.add_sub_strategy(ma, weight=0.5)

        result = comp.remove_sub_strategy("ma_1")
        assert result is True
        assert len(comp.sub_strategies) == 0

    def test_remove_nonexistent(self):
        comp = CompositeStrategy("comp")
        result = comp.remove_sub_strategy("nonexistent")
        assert result is False

    def test_set_weight(self):
        comp = CompositeStrategy("comp")
        ma = MovingAverageCrossStrategy("ma_1")
        comp.add_sub_strategy(ma, weight=0.3)

        comp.set_weight("ma_1", 0.8)
        assert comp.sub_strategies[0].weight == 0.8


class TestWeightedSumMode:
    """加权和模式测试"""

    def test_weighted_sum_buy(self, sample_data):
        """两个 BUY 信号，加权和超过买入阈值"""
        comp = CompositeStrategy(
            "comp",
            voting_mode="weighted_sum",
            threshold_buy=0.2,
            threshold_sell=-0.2,
        )

        # 创建 mock 子策略，固定返回 BUY
        class MockBuyStrategy:
            strategy_id = "mock_buy"
            name = "MockBuy"
            state = "RUNNING"

            def analyze(self, data):
                return {}

            def generate_signals(self, data):
                return [Signal(symbol="600519", action="BUY", strength=0.8, reason="test")]

        comp.add_sub_strategy(MockBuyStrategy(), weight=0.6)
        comp.add_sub_strategy(MockBuyStrategy(), weight=0.4)

        signals = comp.generate_signals(sample_data)
        assert len(signals) == 1
        assert signals[0].action == "BUY"
        assert signals[0].strength > 0

    def test_weighted_sum_hold(self, sample_data):
        """BUY + SELL 信号抵消，加权和在阈值区间内"""
        comp = CompositeStrategy(
            "comp",
            voting_mode="weighted_sum",
            threshold_buy=0.5,
            threshold_sell=-0.5,
        )

        class MockBuyStrategy:
            strategy_id = "mock_buy"
            name = "MockBuy"
            state = "RUNNING"

            def analyze(self, data):
                return {}

            def generate_signals(self, data):
                return [Signal(symbol="600519", action="BUY", strength=0.5, reason="test")]

        class MockSellStrategy:
            strategy_id = "mock_sell"
            name = "MockSell"
            state = "RUNNING"

            def analyze(self, data):
                return {}

            def generate_signals(self, data):
                return [Signal(symbol="600519", action="SELL", strength=0.5, reason="test")]

        comp.add_sub_strategy(MockBuyStrategy(), weight=0.5)
        comp.add_sub_strategy(MockSellStrategy(), weight=0.5)

        signals = comp.generate_signals(sample_data)
        assert len(signals) == 0  # 无信号

    def test_weighted_sum_sell(self, sample_data):
        """SELL 信号加权后低于卖出阈值"""
        comp = CompositeStrategy(
            "comp",
            voting_mode="weighted_sum",
            threshold_buy=0.2,
            threshold_sell=-0.2,
        )

        class MockSellStrategy:
            strategy_id = "mock_sell"
            name = "MockSell"
            state = "RUNNING"

            def analyze(self, data):
                return {}

            def generate_signals(self, data):
                return [Signal(symbol="600519", action="SELL", strength=1.0, reason="test")]

        comp.add_sub_strategy(MockSellStrategy(), weight=1.0)

        signals = comp.generate_signals(sample_data)
        assert len(signals) == 1
        assert signals[0].action == "SELL"


class TestMajorityMode:
    """多数决模式测试"""

    def test_majority_buy(self, sample_data):
        comp = CompositeStrategy(
            "comp",
            voting_mode="majority",
            min_confidence=0.5,
        )

        class MockBuy:
            strategy_id = "buy1"
            name = "Mock"
            state = "RUNNING"

            def analyze(self, data):
                return {}

            def generate_signals(self, data):
                return [Signal(symbol="600519", action="BUY", strength=1.0, reason="test")]

        class MockSell:
            strategy_id = "sell1"
            name = "Mock"
            state = "RUNNING"

            def analyze(self, data):
                return {}

            def generate_signals(self, data):
                return [Signal(symbol="600519", action="SELL", strength=1.0, reason="test")]

        # 2 个 BUY vs 1 个 SELL
        comp.add_sub_strategy(MockBuy(), weight=0.4)
        comp.add_sub_strategy(MockBuy(), weight=0.4)
        comp.add_sub_strategy(MockSell(), weight=0.2)

        signals = comp.generate_signals(sample_data)
        assert len(signals) == 1
        assert signals[0].action == "BUY"

    def test_majority_not_enough_confidence(self, sample_data):
        """票数不足最低置信度，无信号"""
        comp = CompositeStrategy(
            "comp",
            voting_mode="majority",
            min_confidence=0.8,
        )

        class MockBuy:
            strategy_id = "buy1"
            name = "Mock"
            state = "RUNNING"

            def analyze(self, data):
                return {}

            def generate_signals(self, data):
                return [Signal(symbol="600519", action="BUY", strength=0.5, reason="test")]

        comp.add_sub_strategy(MockBuy(), weight=0.5)

        signals = comp.generate_signals(sample_data)
        assert len(signals) == 0  # 0.5 < 0.8 最低置信度


class TestUnanimousMode:
    """一致通过模式测试"""

    def test_unanimous_buy(self, sample_data):
        comp = CompositeStrategy(
            "comp",
            voting_mode="unanimous",
            min_confidence=0.5,
        )

        class MockBuy:
            strategy_id = "buy1"
            name = "Mock"
            state = "RUNNING"

            def analyze(self, data):
                return {}

            def generate_signals(self, data):
                return [Signal(symbol="600519", action="BUY", strength=1.0, reason="test")]

        comp.add_sub_strategy(MockBuy(), weight=0.5)
        comp.add_sub_strategy(MockBuy(), weight=0.5)

        signals = comp.generate_signals(sample_data)
        assert len(signals) == 1
        assert signals[0].action == "BUY"

    def test_unanimous_mixed(self, sample_data):
        """信号方向不一致，无信号"""
        comp = CompositeStrategy(
            "comp",
            voting_mode="unanimous",
            min_confidence=0.5,
        )

        class MockBuy:
            strategy_id = "buy1"
            name = "Mock"
            state = "RUNNING"

            def analyze(self, data):
                return {}

            def generate_signals(self, data):
                return [Signal(symbol="600519", action="BUY", strength=1.0, reason="test")]

        class MockSell:
            strategy_id = "sell1"
            name = "Mock"
            state = "RUNNING"

            def analyze(self, data):
                return {}

            def generate_signals(self, data):
                return [Signal(symbol="600519", action="SELL", strength=1.0, reason="test")]

        comp.add_sub_strategy(MockBuy(), weight=0.5)
        comp.add_sub_strategy(MockSell(), weight=0.5)

        signals = comp.generate_signals(sample_data)
        assert len(signals) == 0


class TestNegativeWeight:
    """负权重测试"""

    def test_negative_weight_reverses_signal(self, sample_data):
        """负权重应反转信号方向"""
        comp = CompositeStrategy(
            "comp",
            voting_mode="majority",
            min_confidence=0.5,
        )

        class MockBuy:
            strategy_id = "buy1"
            name = "Mock"
            state = "RUNNING"

            def analyze(self, data):
                return {}

            def generate_signals(self, data):
                return [Signal(symbol="600519", action="BUY", strength=1.0, reason="test")]

        # 负权重将 BUY 反转为 SELL
        comp.add_sub_strategy(MockBuy(), weight=-1.0)

        signals = comp.generate_signals(sample_data)
        assert len(signals) == 1
        assert signals[0].action == "SELL"


class TestNestedComposite:
    """嵌套组合策略测试"""

    def test_nested_composite(self, sample_data):
        """CompositeStrategy 作为另一个 CompositeStrategy 的子策略"""
        inner = CompositeStrategy(
            "inner",
            voting_mode="weighted_sum",
            threshold_buy=0.1,
            threshold_sell=-0.1,
        )

        class MockBuy:
            strategy_id = "mock"
            name = "Mock"
            state = "RUNNING"

            def analyze(self, data):
                return {}

            def generate_signals(self, data):
                return [Signal(symbol="600519", action="BUY", strength=1.0, reason="test")]

        inner.add_sub_strategy(MockBuy(), weight=1.0)

        outer = CompositeStrategy(
            "outer",
            voting_mode="weighted_sum",
            threshold_buy=0.1,
            threshold_sell=-0.1,
        )
        outer.add_sub_strategy(inner, weight=0.5)
        outer.add_sub_strategy(MockBuy(), weight=0.5)

        signals = outer.generate_signals(sample_data)
        assert len(signals) == 1
        assert signals[0].action == "BUY"


class TestEdgeCases:
    """边界情况测试"""

    def test_empty_sub_strategies(self, sample_data):
        comp = CompositeStrategy("comp")
        signals = comp.generate_signals(sample_data)
        assert signals == []

    def test_all_hold_signals(self, sample_data):
        """所有子策略返回 HOLD，无活跃信号"""
        comp = CompositeStrategy("comp", threshold_buy=0.1)

        class MockHold:
            strategy_id = "hold"
            name = "Mock"
            state = "RUNNING"

            def analyze(self, data):
                return {}

            def generate_signals(self, data):
                return [Signal(symbol="600519", action="HOLD", strength=0.0, reason="test")]

        comp.add_sub_strategy(MockHold(), weight=1.0)
        signals = comp.generate_signals(sample_data)
        assert len(signals) == 0

    def test_get_info(self):
        comp = CompositeStrategy("comp_info", "测试组合")
        info = comp.get_info()
        assert info["strategy_id"] == "comp_info"
        assert info["voting_mode"] == "weighted_sum"
        assert "sub_strategies" in info

    def test_validate_threshold_order(self):
        comp = CompositeStrategy(
            "comp",
            threshold_buy=-0.1,
            threshold_sell=0.1,
        )
        assert comp.validate() is False

    def test_validate_min_confidence(self):
        comp = CompositeStrategy("comp", min_confidence=1.5)
        assert comp.validate() is False
