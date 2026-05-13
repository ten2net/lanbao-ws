"""StrategyFactory 测试"""
import pytest

from lanbao_strategy.strategy_factory import StrategyFactory
from lanbao_strategy.strategy_template import MovingAverageCrossStrategy, RSIStrategy, MACDStrategy
from lanbao_strategy.composite_strategy import CompositeStrategy
from lanbao_strategy.ai_research_strategy import AIResearchStrategy


@pytest.fixture
def factory():
    return StrategyFactory()


class TestBuiltinTemplates:
    """内置模板测试"""

    def test_all_templates_registered(self, factory):
        templates = factory.get_available_templates()
        assert 'ma_cross' in templates
        assert 'rsi' in templates
        assert 'macd' in templates
        assert 'composite' in templates
        assert 'ai_research' in templates

    def test_create_ma_cross(self, factory):
        strategy = factory.create_strategy('ma_cross', 'ma_001', params={
            'fast_period': 10,
            'slow_period': 30
        })
        assert isinstance(strategy, MovingAverageCrossStrategy)
        assert strategy.strategy_id == 'ma_001'
        assert strategy.get_params()['custom']['fast_period'] == 10

    def test_create_rsi(self, factory):
        strategy = factory.create_strategy('rsi', 'rsi_001', params={
            'period': 21,
            'oversold': 25,
            'overbought': 75
        })
        assert isinstance(strategy, RSIStrategy)

    def test_create_macd(self, factory):
        strategy = factory.create_strategy('macd', 'macd_001', params={
            'fast': 8,
            'slow': 21,
            'signal': 5
        })
        assert isinstance(strategy, MACDStrategy)


class TestCompositeCreation:
    """组合策略创建测试"""

    def test_create_composite(self, factory):
        strategy = factory.create_strategy('composite', 'comp_001', params={
            'sub_strategies': [
                {'template_id': 'ma_cross', 'strategy_id': 'ma_sub', 'weight': 0.5},
                {'template_id': 'rsi', 'strategy_id': 'rsi_sub', 'weight': 0.5},
            ],
            'voting_mode': 'weighted_sum',
            'threshold_buy': 0.15,
            'threshold_sell': -0.15,
        })
        assert isinstance(strategy, CompositeStrategy)
        assert strategy.strategy_id == 'comp_001'
        assert len(strategy.sub_strategies) == 2
        assert strategy.voting_mode == 'weighted_sum'

    def test_create_composite_with_custom_params(self, factory):
        strategy = factory.create_strategy('composite', 'comp_002', params={
            'sub_strategies': [
                {
                    'template_id': 'ma_cross',
                    'strategy_id': 'ma_custom',
                    'weight': 0.3,
                    'params': {'fast_period': 5, 'slow_period': 10}
                },
                {
                    'template_id': 'macd',
                    'strategy_id': 'macd_custom',
                    'weight': 0.7,
                    'params': {'fast': 12, 'slow': 26, 'signal': 9}
                },
            ],
            'voting_mode': 'majority',
            'min_confidence': 0.6,
        })
        assert isinstance(strategy, CompositeStrategy)
        assert len(strategy.sub_strategies) == 2
        # 验证子策略参数已正确传递
        ma_params = strategy.sub_strategies[0].strategy.get_params()
        assert ma_params['custom']['fast_period'] == 5

    def test_create_nested_composite(self, factory):
        strategy = factory.create_strategy('composite', 'comp_nested', params={
            'sub_strategies': [
                {
                    'template_id': 'composite',
                    'strategy_id': 'inner_comp',
                    'weight': 0.5,
                    'params': {
                        'sub_strategies': [
                            {'template_id': 'ma_cross', 'strategy_id': 'inner_ma', 'weight': 1.0},
                        ],
                        'voting_mode': 'weighted_sum',
                    }
                },
                {'template_id': 'rsi', 'strategy_id': 'outer_rsi', 'weight': 0.5},
            ],
        })
        assert isinstance(strategy, CompositeStrategy)
        assert len(strategy.sub_strategies) == 2
        # 第一个子策略也是 CompositeStrategy
        assert isinstance(strategy.sub_strategies[0].strategy, CompositeStrategy)


class TestAIResearchCreation:
    """AI 投研策略创建测试"""

    def test_create_ai_research(self, factory):
        strategy = factory.create_strategy('ai_research', 'ai_001', params={
            'symbol': '600519',
            'refresh_interval': 5,
            'expiry_hours': 48.0,
        })
        assert isinstance(strategy, AIResearchStrategy)
        assert strategy.symbol == '600519'
        assert strategy.validate() is True

    def test_create_ai_research_defaults(self, factory):
        strategy = factory.create_strategy('ai_research', 'ai_002', params={
            'symbol': '000001',
        })
        assert isinstance(strategy, AIResearchStrategy)
        assert strategy.symbol == '000001'


class TestValidation:
    """参数验证测试"""

    def test_validate_ma_cross_params(self, factory):
        valid, msg = factory.validate_params('ma_cross', {
            'fast_period': 5,
            'slow_period': 20,
        })
        assert valid is True

    def test_validate_composite_empty_sub(self, factory):
        valid, msg = factory.validate_params('composite', {
            'sub_strategies': [],
        })
        assert valid is False
        assert '至少包含一个子策略' in msg

    def test_validate_composite_too_many_sub(self, factory):
        valid, msg = factory.validate_params('composite', {
            'sub_strategies': [{'template_id': 'ma_cross'}] * 11,
        })
        assert valid is False
        assert '最多支持 10 个' in msg

    def test_validate_composite_threshold_order(self, factory):
        valid, msg = factory.validate_params('composite', {
            'sub_strategies': [
                {'template_id': 'ma_cross', 'weight': 1.0},
            ],
            'threshold_buy': -0.1,
            'threshold_sell': 0.1,
        })
        assert valid is False
        assert 'threshold_buy 必须大于' in msg

    def test_validate_composite_weight_range(self, factory):
        valid, msg = factory.validate_params('composite', {
            'sub_strategies': [
                {'template_id': 'ma_cross', 'weight': 1.5},
            ],
        })
        assert valid is False
        assert '权重' in msg

    def test_validate_composite_min_confidence_range(self, factory):
        valid, msg = factory.validate_params('composite', {
            'sub_strategies': [
                {'template_id': 'ma_cross', 'weight': 1.0},
            ],
            'min_confidence': 1.5,
        })
        assert valid is False
        assert 'min_confidence' in msg

    def test_validate_ai_research_missing_symbol(self, factory):
        valid, msg = factory.validate_params('ai_research', {})
        assert valid is False
        assert 'symbol' in msg

    def test_validate_ai_research_invalid_refresh(self, factory):
        valid, msg = factory.validate_params('ai_research', {
            'symbol': '600519',
            'refresh_interval': 0,
        })
        assert valid is False
        assert 'refresh_interval' in msg

    def test_validate_ai_research_invalid_expiry(self, factory):
        valid, msg = factory.validate_params('ai_research', {
            'symbol': '600519',
            'expiry_hours': -1,
        })
        assert valid is False
        assert 'expiry_hours' in msg

    def test_validate_unknown_template(self, factory):
        valid, msg = factory.validate_params('unknown', {})
        assert valid is False
        assert '模板不存在' in msg

    def test_validate_position_size(self, factory):
        valid, msg = factory.validate_params('ma_cross', {
            'position_size': 1.5,
        })
        assert valid is False
        assert 'position_size' in msg


class TestErrorHandling:
    """错误处理测试"""

    def test_create_unknown_template(self, factory):
        strategy = factory.create_strategy('unknown', 'test')
        assert strategy is None

    def test_create_with_exception(self, factory):
        # 通过 monkeypatch 制造异常
        original = factory._templates.get('ma_cross')
        factory._templates['ma_cross'] = None  # 无效类

        strategy = factory.create_strategy('ma_cross', 'test')
        assert strategy is None

        factory._templates['ma_cross'] = original
