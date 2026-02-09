"""
策略工厂
创建和管理策略实例
"""
from typing import Dict, Type, Optional, Any
from loguru import logger

from .strategy_template import (
    StrategyTemplate,
    MovingAverageCrossStrategy,
    RSIStrategy,
    MACDStrategy
)


class StrategyFactory:
    """
    策略工厂
    
    负责:
    - 创建策略实例
    - 管理策略模板
    - 策略参数验证
    """
    
    def __init__(self):
        self._templates: Dict[str, Type[StrategyTemplate]] = {}
        self._register_builtin_strategies()
    
    def _register_builtin_strategies(self):
        """注册内置策略"""
        self.register_template('ma_cross', MovingAverageCrossStrategy)
        self.register_template('rsi', RSIStrategy)
        self.register_template('macd', MACDStrategy)
    
    def register_template(self, template_id: str, 
                          strategy_class: Type[StrategyTemplate]):
        """
        注册策略模板
        
        Args:
            template_id: 模板ID
            strategy_class: 策略类
        """
        self._templates[template_id] = strategy_class
        logger.info(f"策略模板已注册: {template_id}")
    
    def create_strategy(self, template_id: str, strategy_id: str,
                        name: Optional[str] = None,
                        params: Optional[Dict[str, Any]] = None) -> Optional[StrategyTemplate]:
        """
        创建策略实例
        
        Args:
            template_id: 模板ID
            strategy_id: 策略ID
            name: 策略名称
            params: 策略参数
            
        Returns:
            策略实例
        """
        strategy_class = self._templates.get(template_id)
        if not strategy_class:
            logger.error(f"策略模板不存在: {template_id}")
            return None
        
        try:
            if name is None:
                name = f"{template_id}_{strategy_id}"
            
            # 根据模板类型创建实例
            if template_id == 'ma_cross':
                fast = params.get('fast_period', 5) if params else 5
                slow = params.get('slow_period', 20) if params else 20
                strategy = MovingAverageCrossStrategy(
                    strategy_id=strategy_id,
                    name=name,
                    fast_period=fast,
                    slow_period=slow
                )
            elif template_id == 'rsi':
                period = params.get('period', 14) if params else 14
                oversold = params.get('oversold', 30) if params else 30
                overbought = params.get('overbought', 70) if params else 70
                strategy = RSIStrategy(
                    strategy_id=strategy_id,
                    name=name,
                    period=period,
                    oversold=oversold,
                    overbought=overbought
                )
            elif template_id == 'macd':
                fast = params.get('fast', 12) if params else 12
                slow = params.get('slow', 26) if params else 26
                signal = params.get('signal', 9) if params else 9
                strategy = MACDStrategy(
                    strategy_id=strategy_id,
                    name=name,
                    fast=fast,
                    slow=slow,
                    signal=signal
                )
            else:
                strategy = strategy_class(strategy_id, name)
            
            logger.info(f"策略已创建: {strategy_id} (模板: {template_id})")
            return strategy
            
        except Exception as e:
            logger.error(f"创建策略失败: {e}")
            return None
    
    def get_available_templates(self) -> Dict[str, str]:
        """获取可用模板列表"""
        return {
            'ma_cross': '双均线交叉策略',
            'rsi': 'RSI策略',
            'macd': 'MACD策略'
        }
    
    def validate_params(self, template_id: str, 
                        params: Dict[str, Any]) -> tuple[bool, str]:
        """
        验证策略参数
        
        Args:
            template_id: 模板ID
            params: 参数
            
        Returns:
            (是否有效, 错误信息)
        """
        if template_id not in self._templates:
            return False, f"模板不存在: {template_id}"
        
        # 基础参数验证
        if 'position_size' in params:
            if not 0 < params['position_size'] <= 1:
                return False, "position_size 必须在 (0, 1] 之间"
        
        if 'stop_loss' in params:
            if not 0 < params['stop_loss'] <= 1:
                return False, "stop_loss 必须在 (0, 1] 之间"
        
        return True, "参数有效"
