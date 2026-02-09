"""
策略模板基类
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
import pandas as pd
import numpy as np
from loguru import logger


@dataclass
class Signal:
    """交易信号"""
    symbol: str
    action: str  # BUY, SELL, HOLD
    strength: float  # 信号强度 0.0-1.0
    reason: str
    timestamp: datetime = field(default_factory=datetime.now)
    params: Dict[str, Any] = field(default_factory=dict)


@dataclass
class StrategyParams:
    """策略参数"""
    lookback_period: int = 20
    position_size: float = 0.1
    stop_loss: float = 0.05
    take_profit: float = 0.1
    custom: Dict[str, Any] = field(default_factory=dict)


class StrategyTemplate(ABC):
    """
    策略模板基类
    
    所有策略必须继承此类并实现抽象方法
    """
    
    def __init__(self, strategy_id: str, name: str, params: Optional[StrategyParams] = None):
        """
        初始化策略
        
        Args:
            strategy_id: 策略ID
            name: 策略名称
            params: 策略参数
        """
        self._strategy_id = strategy_id
        self._name = name
        self._params = params or StrategyParams()
        self._signals: List[Signal] = []
        self._state = "INITIALIZED"
        self._performance = {}
        
    @property
    def strategy_id(self) -> str:
        """策略ID"""
        return self._strategy_id
    
    @property
    def name(self) -> str:
        """策略名称"""
        return self._name
    
    @property
    def state(self) -> str:
        """策略状态"""
        return self._state
    
    @abstractmethod
    def analyze(self, data: pd.DataFrame) -> Dict[str, Any]:
        """
        分析市场数据
        
        Args:
            data: 市场数据DataFrame (OHLCV)
            
        Returns:
            分析结果字典
        """
        pass
    
    @abstractmethod
    def generate_signals(self, data: pd.DataFrame) -> List[Signal]:
        """
        生成交易信号
        
        Args:
            data: 市场数据
            
        Returns:
            信号列表
        """
        pass
    
    def on_data(self, data: pd.DataFrame) -> List[Signal]:
        """
        接收新数据
        
        Args:
            data: 新数据
            
        Returns:
            生成的信号
        """
        try:
            # 分析数据
            analysis = self.analyze(data)
            
            # 生成信号
            signals = self.generate_signals(data)
            
            # 记录信号
            self._signals.extend(signals)
            
            return signals
            
        except Exception as e:
            logger.error(f"[{self._strategy_id}] 处理数据失败: {e}")
            return []
    
    def update_params(self, **kwargs):
        """
        更新策略参数
        
        Args:
            **kwargs: 参数键值对
        """
        for key, value in kwargs.items():
            if hasattr(self._params, key):
                setattr(self._params, key, value)
                logger.info(f"[{self._strategy_id}] 更新参数 {key} = {value}")
            else:
                self._params.custom[key] = value
    
    def get_params(self) -> Dict[str, Any]:
        """获取策略参数"""
        return {
            'lookback_period': self._params.lookback_period,
            'position_size': self._params.position_size,
            'stop_loss': self._params.stop_loss,
            'take_profit': self._params.take_profit,
            'custom': self._params.custom
        }
    
    def get_signals(self, limit: int = 100) -> List[Signal]:
        """获取信号历史"""
        return self._signals[-limit:]
    
    def clear_signals(self):
        """清空信号历史"""
        self._signals.clear()
    
    def set_state(self, state: str):
        """设置策略状态"""
        self._state = state
        logger.info(f"[{self._strategy_id}] 状态变更为: {state}")
    
    def validate(self) -> bool:
        """
        验证策略配置
        
        Returns:
            是否有效
        """
        return True
    
    def get_info(self) -> Dict[str, Any]:
        """获取策略信息"""
        return {
            'strategy_id': self._strategy_id,
            'name': self._name,
            'state': self._state,
            'params': self.get_params(),
            'signal_count': len(self._signals)
        }


class MovingAverageCrossStrategy(StrategyTemplate):
    """
    双均线交叉策略
    
    金叉买入，死叉卖出
    """
    
    def __init__(self, strategy_id: str = "ma_cross", 
                 name: str = "双均线交叉策略",
                 fast_period: int = 5,
                 slow_period: int = 20):
        params = StrategyParams(
            custom={'fast_period': fast_period, 'slow_period': slow_period}
        )
        super().__init__(strategy_id, name, params)
    
    def analyze(self, data: pd.DataFrame) -> Dict[str, Any]:
        """分析市场趋势"""
        df = data.copy()
        fast = self._params.custom.get('fast_period', 5)
        slow = self._params.custom.get('slow_period', 20)
        
        df['ma_fast'] = df['close'].rolling(fast).mean()
        df['ma_slow'] = df['close'].rolling(slow).mean()
        
        # 计算趋势强度
        latest = df.iloc[-1]
        diff = latest['ma_fast'] - latest['ma_slow']
        trend_strength = abs(diff) / latest['close'] if latest['close'] > 0 else 0
        
        return {
            'trend': 'UP' if diff > 0 else 'DOWN',
            'trend_strength': trend_strength,
            'ma_fast': latest['ma_fast'],
            'ma_slow': latest['ma_slow']
        }
    
    def generate_signals(self, data: pd.DataFrame) -> List[Signal]:
        """生成交易信号"""
        df = data.copy()
        fast = self._params.custom.get('fast_period', 5)
        slow = self._params.custom.get('slow_period', 20)
        
        df['ma_fast'] = df['close'].rolling(fast).mean()
        df['ma_slow'] = df['close'].rolling(slow).mean()
        
        signals = []
        symbol = df.get('symbol', ['UNKNOWN'])[0] if 'symbol' in df.columns else 'UNKNOWN'
        
        # 计算交叉
        df['cross'] = 0
        df.loc[df['ma_fast'] > df['ma_slow'], 'cross'] = 1
        df.loc[df['ma_fast'] < df['ma_slow'], 'cross'] = -1
        df['cross_signal'] = df['cross'].diff()
        
        # 生成信号
        latest = df.iloc[-1]
        if latest['cross_signal'] == 2:  # 0 -> 1 金叉
            signals.append(Signal(
                symbol=symbol,
                action='BUY',
                strength=0.8,
                reason=f"金叉: MA{fast}上穿MA{slow}"
            ))
        elif latest['cross_signal'] == -2:  # 0 -> -1 死叉
            signals.append(Signal(
                symbol=symbol,
                action='SELL',
                strength=0.8,
                reason=f"死叉: MA{fast}下穿MA{slow}"
            ))
        
        return signals


class RSIStrategy(StrategyTemplate):
    """
    RSI策略
    
    超卖买入，超买卖出
    """
    
    def __init__(self, strategy_id: str = "rsi",
                 name: str = "RSI策略",
                 period: int = 14,
                 oversold: int = 30,
                 overbought: int = 70):
        params = StrategyParams(
            custom={'period': period, 'oversold': oversold, 'overbought': overbought}
        )
        super().__init__(strategy_id, name, params)
    
    def analyze(self, data: pd.DataFrame) -> Dict[str, Any]:
        """分析RSI指标"""
        df = data.copy()
        period = self._params.custom.get('period', 14)
        
        # 计算RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        latest = df.iloc[-1]
        rsi = latest['rsi']
        
        return {
            'rsi': rsi,
            'momentum': 'OVERBOUGHT' if rsi > 70 else 'OVERSOLD' if rsi < 30 else 'NEUTRAL'
        }
    
    def generate_signals(self, data: pd.DataFrame) -> List[Signal]:
        """生成交易信号"""
        df = data.copy()
        period = self._params.custom.get('period', 14)
        oversold = self._params.custom.get('oversold', 30)
        overbought = self._params.custom.get('overbought', 70)
        
        # 计算RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        signals = []
        symbol = df.get('symbol', ['UNKNOWN'])[0] if 'symbol' in df.columns else 'UNKNOWN'
        
        latest = df.iloc[-1]
        prev = df.iloc[-2] if len(df) > 1 else latest
        
        # 超卖买入
        if prev['rsi'] < oversold and latest['rsi'] >= oversold:
            signals.append(Signal(
                symbol=symbol,
                action='BUY',
                strength=0.7,
                reason=f"RSI({period})超卖回升: {latest['rsi']:.1f}"
            ))
        
        # 超买卖出
        if prev['rsi'] > overbought and latest['rsi'] <= overbought:
            signals.append(Signal(
                symbol=symbol,
                action='SELL',
                strength=0.7,
                reason=f"RSI({period})超买回落: {latest['rsi']:.1f}"
            ))
        
        return signals


class MACDStrategy(StrategyTemplate):
    """
    MACD策略
    
    MACD金叉买入，死叉卖出
    """
    
    def __init__(self, strategy_id: str = "macd",
                 name: str = "MACD策略",
                 fast: int = 12,
                 slow: int = 26,
                 signal: int = 9):
        params = StrategyParams(
            custom={'fast': fast, 'slow': slow, 'signal': signal}
        )
        super().__init__(strategy_id, name, params)
    
    def analyze(self, data: pd.DataFrame) -> Dict[str, Any]:
        """分析MACD指标"""
        df = data.copy()
        fast = self._params.custom.get('fast', 12)
        slow = self._params.custom.get('slow', 26)
        signal_period = self._params.custom.get('signal', 9)
        
        # 计算MACD
        exp1 = df['close'].ewm(span=fast, adjust=False).mean()
        exp2 = df['close'].ewm(span=slow, adjust=False).mean()
        df['macd'] = exp1 - exp2
        df['signal'] = df['macd'].ewm(span=signal_period, adjust=False).mean()
        df['histogram'] = df['macd'] - df['signal']
        
        latest = df.iloc[-1]
        
        return {
            'macd': latest['macd'],
            'signal': latest['signal'],
            'histogram': latest['histogram'],
            'trend': 'BULLISH' if latest['histogram'] > 0 else 'BEARISH'
        }
    
    def generate_signals(self, data: pd.DataFrame) -> List[Signal]:
        """生成交易信号"""
        df = data.copy()
        fast = self._params.custom.get('fast', 12)
        slow = self._params.custom.get('slow', 26)
        signal_period = self._params.custom.get('signal', 9)
        
        # 计算MACD
        exp1 = df['close'].ewm(span=fast, adjust=False).mean()
        exp2 = df['close'].ewm(span=slow, adjust=False).mean()
        df['macd'] = exp1 - exp2
        df['signal'] = df['macd'].ewm(span=signal_period, adjust=False).mean()
        df['histogram'] = df['macd'] - df['signal']
        
        signals = []
        symbol = df.get('symbol', ['UNKNOWN'])[0] if 'symbol' in df.columns else 'UNKNOWN'
        
        latest = df.iloc[-1]
        prev = df.iloc[-2] if len(df) > 1 else latest
        
        # MACD金叉 (histogram由负变正)
        if prev['histogram'] < 0 and latest['histogram'] >= 0:
            signals.append(Signal(
                symbol=symbol,
                action='BUY',
                strength=0.75,
                reason=f"MACD金叉"
            ))
        
        # MACD死叉 (histogram由正变负)
        if prev['histogram'] > 0 and latest['histogram'] <= 0:
            signals.append(Signal(
                symbol=symbol,
                action='SELL',
                strength=0.75,
                reason=f"MACD死叉"
            ))
        
        return signals
