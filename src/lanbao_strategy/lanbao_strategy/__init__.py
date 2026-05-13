"""
揽宝策略服务模块
"""

from .strategy_template import StrategyTemplate, MovingAverageCrossStrategy
from .strategy_manager import StrategyManager
from .strategy_factory import StrategyFactory
from .composite_strategy import CompositeStrategy, SubStrategyConfig
from .ai_research_strategy import AIResearchStrategy

__all__ = [
    'StrategyTemplate',
    'MovingAverageCrossStrategy',
    'StrategyManager',
    'StrategyFactory',
    'CompositeStrategy',
    'SubStrategyConfig',
    'AIResearchStrategy',
]
