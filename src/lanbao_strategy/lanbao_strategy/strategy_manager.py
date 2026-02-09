"""
策略管理器
管理策略的生命周期
"""
from typing import Dict, List, Optional, Any
from datetime import datetime
from loguru import logger

from .strategy_template import StrategyTemplate


class StrategyManager:
    """
    策略管理器
    
    管理多个策略的生命周期:
    - 创建
    - 启动
    - 暂停
    - 停止
    - 删除
    """
    
    def __init__(self):
        self._strategies: Dict[str, StrategyTemplate] = {}
        self._history: List[Dict] = []
    
    def register(self, strategy: StrategyTemplate) -> bool:
        """
        注册策略
        
        Args:
            strategy: 策略实例
            
        Returns:
            是否成功
        """
        strategy_id = strategy.strategy_id
        
        if strategy_id in self._strategies:
            logger.warning(f"策略已存在: {strategy_id}")
            return False
        
        self._strategies[strategy_id] = strategy
        strategy.set_state("REGISTERED")
        
        self._history.append({
            'action': 'REGISTER',
            'strategy_id': strategy_id,
            'timestamp': datetime.now()
        })
        
        logger.info(f"策略已注册: {strategy_id}")
        return True
    
    def unregister(self, strategy_id: str) -> bool:
        """
        注销策略
        
        Args:
            strategy_id: 策略ID
            
        Returns:
            是否成功
        """
        if strategy_id not in self._strategies:
            logger.warning(f"策略不存在: {strategy_id}")
            return False
        
        strategy = self._strategies[strategy_id]
        strategy.set_state("UNREGISTERED")
        
        del self._strategies[strategy_id]
        
        self._history.append({
            'action': 'UNREGISTER',
            'strategy_id': strategy_id,
            'timestamp': datetime.now()
        })
        
        logger.info(f"策略已注销: {strategy_id}")
        return True
    
    def start(self, strategy_id: str) -> bool:
        """
        启动策略
        
        Args:
            strategy_id: 策略ID
            
        Returns:
            是否成功
        """
        strategy = self._strategies.get(strategy_id)
        if not strategy:
            logger.warning(f"策略不存在: {strategy_id}")
            return False
        
        if strategy.state == "RUNNING":
            logger.warning(f"策略已在运行: {strategy_id}")
            return True
        
        strategy.set_state("RUNNING")
        
        self._history.append({
            'action': 'START',
            'strategy_id': strategy_id,
            'timestamp': datetime.now()
        })
        
        logger.info(f"策略已启动: {strategy_id}")
        return True
    
    def stop(self, strategy_id: str) -> bool:
        """
        停止策略
        
        Args:
            strategy_id: 策略ID
            
        Returns:
            是否成功
        """
        strategy = self._strategies.get(strategy_id)
        if not strategy:
            logger.warning(f"策略不存在: {strategy_id}")
            return False
        
        strategy.set_state("STOPPED")
        
        self._history.append({
            'action': 'STOP',
            'strategy_id': strategy_id,
            'timestamp': datetime.now()
        })
        
        logger.info(f"策略已停止: {strategy_id}")
        return True
    
    def pause(self, strategy_id: str) -> bool:
        """
        暂停策略
        
        Args:
            strategy_id: 策略ID
            
        Returns:
            是否成功
        """
        strategy = self._strategies.get(strategy_id)
        if not strategy:
            logger.warning(f"策略不存在: {strategy_id}")
            return False
        
        if strategy.state != "RUNNING":
            logger.warning(f"策略未在运行: {strategy_id}")
            return False
        
        strategy.set_state("PAUSED")
        
        self._history.append({
            'action': 'PAUSE',
            'strategy_id': strategy_id,
            'timestamp': datetime.now()
        })
        
        logger.info(f"策略已暂停: {strategy_id}")
        return True
    
    def resume(self, strategy_id: str) -> bool:
        """
        恢复策略
        
        Args:
            strategy_id: 策略ID
            
        Returns:
            是否成功
        """
        strategy = self._strategies.get(strategy_id)
        if not strategy:
            logger.warning(f"策略不存在: {strategy_id}")
            return False
        
        if strategy.state != "PAUSED":
            logger.warning(f"策略未暂停: {strategy_id}")
            return False
        
        strategy.set_state("RUNNING")
        
        self._history.append({
            'action': 'RESUME',
            'strategy_id': strategy_id,
            'timestamp': datetime.now()
        })
        
        logger.info(f"策略已恢复: {strategy_id}")
        return True
    
    def update_params(self, strategy_id: str, **params) -> bool:
        """
        更新策略参数
        
        Args:
            strategy_id: 策略ID
            **params: 参数
            
        Returns:
            是否成功
        """
        strategy = self._strategies.get(strategy_id)
        if not strategy:
            logger.warning(f"策略不存在: {strategy_id}")
            return False
        
        strategy.update_params(**params)
        
        self._history.append({
            'action': 'UPDATE_PARAMS',
            'strategy_id': strategy_id,
            'params': params,
            'timestamp': datetime.now()
        })
        
        return True
    
    def get_strategy(self, strategy_id: str) -> Optional[StrategyTemplate]:
        """获取策略"""
        return self._strategies.get(strategy_id)
    
    def get_all_strategies(self) -> Dict[str, StrategyTemplate]:
        """获取所有策略"""
        return self._strategies.copy()
    
    def get_running_strategies(self) -> Dict[str, StrategyTemplate]:
        """获取运行中的策略"""
        return {
            k: v for k, v in self._strategies.items()
            if v.state == "RUNNING"
        }
    
    def get_strategy_info(self, strategy_id: str) -> Optional[Dict]:
        """获取策略信息"""
        strategy = self._strategies.get(strategy_id)
        if strategy:
            return strategy.get_info()
        return None
    
    def get_all_info(self) -> List[Dict]:
        """获取所有策略信息"""
        return [s.get_info() for s in self._strategies.values()]
    
    def get_history(self, strategy_id: Optional[str] = None) -> List[Dict]:
        """获取操作历史"""
        if strategy_id:
            return [h for h in self._history if h['strategy_id'] == strategy_id]
        return self._history.copy()
