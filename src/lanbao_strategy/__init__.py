# 仅导出非ROS2依赖的工具类
try:
    from .lanbao_strategy.strategy_template import StrategyTemplate, MovingAverageCrossStrategy
    __all__ = ['StrategyTemplate', 'MovingAverageCrossStrategy']
except ImportError:
    __all__ = []
