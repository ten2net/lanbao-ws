"""
揽宝策略节点基类
"""
from abc import abstractmethod
from typing import Dict, List, Optional, Any
import pandas as pd
import numpy as np
from dataclasses import dataclass
from loguru import logger

from .base_node import LanBaoBaseNode
from lanbao_interfaces.msg import StockSignal, MarketAssessment


@dataclass
class StrategyParameters:
    """策略参数"""
    lookback_period: int = 20
    entry_threshold: float = 0.02
    exit_threshold: float = 0.01
    position_size: float = 0.1
    stop_loss: float = 0.05
    take_profit: float = 0.1
    custom_params: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.custom_params is None:
            self.custom_params = {}


class StrategyNode(LanBaoBaseNode):
    """
    策略节点基类
    
    负责:
    - 市场环境评估
    - 交易信号生成
    - 策略参数管理
    """
    
    def __init__(self, node_name: str, config=None):
        super().__init__(node_name, config)
        self._node_config.node_type = "strategy"
        self._parameters: StrategyParameters = StrategyParameters()
        self._performance_tracker = PerformanceTracker()
        self._signal_history: List[StockSignal] = []
        
    def initialize(self) -> bool:
        """初始化策略节点"""
        try:
            # 加载策略参数
            self._load_parameters()
            
            # 注册健康检查
            self._health.register_check(
                'strategy_health',
                self._check_strategy_health,
                interval_seconds=60
            )
            
            logger.info(f"[{self.get_name()}] 策略节点初始化完成")
            return True
            
        except Exception as e:
            logger.error(f"[{self.get_name()}] 策略节点初始化失败: {e}")
            return False
    
    def _load_parameters(self):
        """加载策略参数"""
        params = self._node_config.parameters.get('strategy', {})
        self._parameters = StrategyParameters(
            lookback_period=params.get('lookback_period', 20),
            entry_threshold=params.get('entry_threshold', 0.02),
            exit_threshold=params.get('exit_threshold', 0.01),
            position_size=params.get('position_size', 0.1),
            stop_loss=params.get('stop_loss', 0.05),
            take_profit=params.get('take_profit', 0.1),
            custom_params=params.get('custom', {})
        )
    
    @abstractmethod
    def evaluate_market(self, market_data: pd.DataFrame) -> MarketAssessment:
        """
        评估市场环境
        
        Args:
            market_data: 市场数据
            
        Returns:
            市场评估结果
        """
        pass
    
    @abstractmethod
    def generate_signals(self, data: pd.DataFrame) -> List[StockSignal]:
        """
        生成交易信号
        
        Args:
            data: 股票数据
            
        Returns:
            交易信号列表
        """
        pass
    
    def update_parameters(self, **kwargs):
        """
        更新策略参数
        
        Args:
            **kwargs: 要更新的参数
        """
        for key, value in kwargs.items():
            if hasattr(self._parameters, key):
                setattr(self._parameters, key, value)
                logger.info(f"[{self.get_name()}] 更新参数 {key} = {value}")
            else:
                self._parameters.custom_params[key] = value
    
    def calculate_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        计算技术指标
        
        Args:
            data: 原始数据，需要包含 OHLCV
            
        Returns:
            添加了技术指标的数据
        """
        df = data.copy()
        
        # 移动平均线
        df['ma5'] = df['close'].rolling(window=5).mean()
        df['ma10'] = df['close'].rolling(window=10).mean()
        df['ma20'] = df['close'].rolling(window=20).mean()
        df['ma60'] = df['close'].rolling(window=60).mean()
        
        # RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # MACD
        exp1 = df['close'].ewm(span=12, adjust=False).mean()
        exp2 = df['close'].ewm(span=26, adjust=False).mean()
        df['macd'] = exp1 - exp2
        df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
        df['macd_hist'] = df['macd'] - df['macd_signal']
        
        # 布林带
        df['boll_mid'] = df['close'].rolling(window=20).mean()
        boll_std = df['close'].rolling(window=20).std()
        df['boll_upper'] = df['boll_mid'] + 2 * boll_std
        df['boll_lower'] = df['boll_mid'] - 2 * boll_std
        
        # 波动率
        df['volatility'] = df['close'].pct_change().rolling(window=20).std()
        
        return df
    
    def _check_strategy_health(self) -> Dict:
        """检查策略健康状态"""
        performance = self._performance_tracker.get_summary()
        
        # 根据策略表现判断健康状态
        if performance.get('total_return', 0) < -0.2:  # 亏损超过20%
            return {
                'status': HealthStatus.DEGRADED,
                'message': '策略表现不佳，建议检查',
                'metadata': performance
            }
        
        return {
            'status': HealthStatus.HEALTHY,
            'message': '策略运行正常',
            'metadata': performance
        }
    
    def record_signal(self, signal: StockSignal):
        """记录信号"""
        self._signal_history.append(signal)
        self._performance_tracker.record_signal(signal)
        self._metrics.increment_counter('signals_generated')
    
    def get_signal_history(self, limit: int = 100) -> List[StockSignal]:
        """获取信号历史"""
        return self._signal_history[-limit:]


class PerformanceTracker:
    """策略表现追踪器"""
    
    def __init__(self):
        self._signals: List[Dict] = []
        self._returns: List[float] = []
        
    def record_signal(self, signal: StockSignal):
        """记录信号"""
        self._signals.append({
            'symbol': signal.symbol,
            'type': signal.signal_type,
            'timestamp': signal.timestamp,
            'strength': signal.strength
        })
    
    def record_return(self, ret: float):
        """记录收益"""
        self._returns.append(ret)
    
    def get_summary(self) -> Dict:
        """获取表现摘要"""
        if not self._returns:
            return {'total_return': 0, 'signal_count': len(self._signals)}
        
        returns = np.array(self._returns)
        return {
            'total_return': float(np.sum(returns)),
            'mean_return': float(np.mean(returns)),
            'std_return': float(np.std(returns)),
            'sharpe': float(np.mean(returns) / np.std(returns)) if np.std(returns) > 0 else 0,
            'win_rate': float(np.sum(returns > 0) / len(returns)),
            'signal_count': len(self._signals)
        }


# 导入HealthStatus
from .health_monitor import HealthStatus
