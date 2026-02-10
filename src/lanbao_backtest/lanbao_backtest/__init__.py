"""
揽宝回测引擎模块
"""

from .backtest_engine import BacktestEngine, BacktestConfig
from .performance_analyzer import PerformanceAnalyzer

# 仅在ROS2可用时导入节点类
try:
    from .backtest_engine_node import BacktestEngineNode
    NODE_AVAILABLE = True
except ImportError:
    BacktestEngineNode = None
    NODE_AVAILABLE = False

__all__ = [
    'BacktestEngine',
    'BacktestConfig',
    'PerformanceAnalyzer',
] + (['BacktestEngineNode'] if NODE_AVAILABLE else [])
