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
from .composite_strategy import CompositeStrategy, SubStrategyConfig
from .ai_research_strategy import AIResearchStrategy


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
        self.register_template('composite', CompositeStrategy)
        self.register_template('ai_research', AIResearchStrategy)
    
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
            elif template_id == 'composite':
                strategy = self._create_composite_strategy(
                    strategy_id, name, params
                )
            elif template_id == 'ai_research':
                strategy = self._create_ai_research_strategy(
                    strategy_id, name, params
                )
            else:
                strategy = strategy_class(strategy_id, name)
            
            logger.info(f"策略已创建: {strategy_id} (模板: {template_id})")
            return strategy
            
        except Exception as e:
            logger.error(f"创建策略失败: {e}")
            return None
    
    def _create_composite_strategy(self, strategy_id: str, name: str,
                                    params: Optional[Dict[str, Any]]) -> CompositeStrategy:
        """创建组合策略实例"""
        p = params or {}

        # 创建子策略
        sub_configs = p.get('sub_strategies', [])
        sub_strategy_configs = []

        for cfg in sub_configs:
            if isinstance(cfg, dict):
                sub_template_id = cfg.get('template_id')
                sub_strategy_id = cfg.get('strategy_id', f"{strategy_id}_sub_{len(sub_strategy_configs)}")
                sub_params = cfg.get('params', {})
                sub_weight = cfg.get('weight', 1.0)

                sub_strategy = self.create_strategy(
                    template_id=sub_template_id,
                    strategy_id=sub_strategy_id,
                    params=sub_params
                )
                if sub_strategy:
                    sub_strategy_configs.append({
                        'strategy': sub_strategy,
                        'weight': sub_weight,
                    })
            elif isinstance(cfg, SubStrategyConfig):
                sub_strategy_configs.append(cfg)

        return CompositeStrategy(
            strategy_id=strategy_id,
            name=name,
            sub_strategies=sub_strategy_configs,
            voting_mode=p.get('voting_mode', 'weighted_sum'),
            threshold_buy=p.get('threshold_buy', 0.2),
            threshold_sell=p.get('threshold_sell', -0.2),
            min_confidence=p.get('min_confidence', 0.5),
        )

    def _create_ai_research_strategy(self, strategy_id: str, name: str,
                                      params: Optional[Dict[str, Any]]) -> AIResearchStrategy:
        """创建AI投研策略实例"""
        p = params or {}
        return AIResearchStrategy(
            strategy_id=strategy_id,
            name=name,
            symbol=p.get('symbol', ''),
            refresh_interval=p.get('refresh_interval', 1),
            expiry_hours=p.get('expiry_hours', 24.0),
        )

    def get_available_templates(self) -> Dict[str, str]:
        """获取可用模板列表"""
        return {
            'ma_cross': '双均线交叉策略',
            'rsi': 'RSI策略',
            'macd': 'MACD策略',
            'composite': '组合策略（信号叠加器）',
            'ai_research': 'AI投研策略',
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

        # 组合策略参数验证
        if template_id == 'composite':
            sub_strategies = params.get('sub_strategies', [])
            if not sub_strategies:
                return False, "composite 策略必须至少包含一个子策略"
            if len(sub_strategies) > 10:
                return False, "composite 策略最多支持 10 个子策略"

            threshold_buy = params.get('threshold_buy', 0.2)
            threshold_sell = params.get('threshold_sell', -0.2)
            if threshold_buy <= threshold_sell:
                return False, "threshold_buy 必须大于 threshold_sell"

            min_confidence = params.get('min_confidence', 0.5)
            if not 0 <= min_confidence <= 1:
                return False, "min_confidence 必须在 [0, 1] 之间"

            # 验证权重
            for cfg in sub_strategies:
                if isinstance(cfg, dict) and 'weight' in cfg:
                    w = cfg['weight']
                    if not -1 <= w <= 1:
                        return False, f"子策略权重 {w} 必须在 [-1, 1] 之间"

        # AI投研策略参数验证
        if template_id == 'ai_research':
            if not params.get('symbol'):
                return False, "ai_research 策略必须指定 symbol"
            refresh = params.get('refresh_interval', 1)
            if refresh < 1:
                return False, "refresh_interval 必须 >= 1"
            expiry = params.get('expiry_hours', 24.0)
            if expiry <= 0:
                return False, "expiry_hours 必须 > 0"

        return True, "参数有效"
