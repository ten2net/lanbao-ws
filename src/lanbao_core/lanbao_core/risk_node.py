"""
揽宝风险控制节点基类
"""
from abc import abstractmethod
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum
from loguru import logger

from .base_node import LanBaoBaseNode
from lanbao_interfaces.msg import RiskAlert, TradeSignal, PortfolioStatus


class RiskLevel(Enum):
    """风险等级"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class RiskLimits:
    """风险限制"""
    max_position_size: float = 0.2  # 最大单仓比例
    max_drawdown: float = 0.1  # 最大回撤
    max_daily_loss: float = 0.05  # 最大日亏损
    max_concentration: float = 0.3  # 最大集中度
    volatility_limit: float = 0.3  # 波动率限制


class RiskControlNode(LanBaoBaseNode):
    """
    风险控制节点基类
    
    负责:
    - 实时风险监控
    - 交易前风险检查
    - 风险告警生成
    """
    
    def __init__(self, node_name: str, config=None):
        super().__init__(node_name, config)
        self._node_config.node_type = "risk_control"
        self._risk_limits = RiskLimits()
        self._risk_rules: List[Any] = []
        self._alert_history: List[RiskAlert] = []
        self._circuit_breaker_active = False
        
    def initialize(self) -> bool:
        """初始化风控节点"""
        try:
            # 加载风险限制
            self._load_risk_limits()
            
            # 设置风险规则
            self._setup_risk_rules()
            
            # 注册健康检查
            self._health.register_check(
                'risk_system_health',
                self._check_risk_system,
                interval_seconds=30
            )
            
            logger.info(f"[{self.get_name()}] 风控节点初始化完成")
            return True
            
        except Exception as e:
            logger.error(f"[{self.get_name()}] 风控节点初始化失败: {e}")
            return False
    
    def _load_risk_limits(self):
        """加载风险限制"""
        limits = self._node_config.parameters.get('risk_limits', {})
        self._risk_limits = RiskLimits(
            max_position_size=limits.get('max_position_size', 0.2),
            max_drawdown=limits.get('max_drawdown', 0.1),
            max_daily_loss=limits.get('max_daily_loss', 0.05),
            max_concentration=limits.get('max_concentration', 0.3),
            volatility_limit=limits.get('volatility_limit', 0.3)
        )
    
    @abstractmethod
    def _setup_risk_rules(self):
        """
        设置风险规则
        子类必须实现此方法
        """
        pass
    
    @abstractmethod
    def check_risk(self, signal: TradeSignal, portfolio: PortfolioStatus) -> Dict[str, Any]:
        """
        检查风险
        
        Args:
            signal: 交易信号
            portfolio: 当前持仓
            
        Returns:
            风险检查结果
        """
        pass
    
    def evaluate_position_risk(self, portfolio: PortfolioStatus) -> RiskLevel:
        """
        评估持仓风险
        
        Args:
            portfolio: 当前持仓
            
        Returns:
            风险等级
        """
        # 检查回撤
        if abs(portfolio.drawdown) > self._risk_limits.max_drawdown:
            return RiskLevel.CRITICAL
        
        # 检查日亏损
        if portfolio.day_pnl < -portfolio.total_value * self._risk_limits.max_daily_loss:
            return RiskLevel.HIGH
        
        # 检查集中度
        # (简化处理，实际需要遍历持仓)
        
        return RiskLevel.LOW
    
    def check_trade_allowed(self, signal: TradeSignal, portfolio: PortfolioStatus) -> bool:
        """
        检查交易是否允许
        
        Args:
            signal: 交易信号
            portfolio: 当前持仓
            
        Returns:
            是否允许交易
        """
        # 检查熔断
        if self._circuit_breaker_active:
            logger.warning("熔断机制已激活，拒绝交易")
            return False
        
        # 检查风险
        result = self.check_risk(signal, portfolio)
        if result.get('risk_score', 0) > 0.8:
            logger.warning(f"风险评分过高: {result.get('risk_score')}")
            return False
        
        return True
    
    def generate_alert(self, alert_type: str, level: RiskLevel, 
                       message: str, current_value: float, threshold: float) -> RiskAlert:
        """
        生成风险告警
        
        Args:
            alert_type: 告警类型
            level: 风险等级
            message: 告警消息
            current_value: 当前值
            threshold: 阈值
            
        Returns:
            风险告警消息
        """
        alert = RiskAlert()
        alert.alert_id = f"{alert_type}_{int(self.get_clock().now().seconds_nanoseconds()[0])}"
        alert.alert_type = alert_type
        alert.level = level.value
        alert.message = message
        alert.current_value = current_value
        alert.threshold = threshold
        alert.timestamp = int(self.get_clock().now().seconds_nanoseconds()[0])
        
        self._alert_history.append(alert)
        
        # 发布告警
        # self._alert_publisher.publish(alert)
        
        logger.warning(f"[风险告警] [{level.value}] {message}")
        
        return alert
    
    def activate_circuit_breaker(self, reason: str):
        """
        激活熔断机制
        
        Args:
            reason: 熔断原因
        """
        self._circuit_breaker_active = True
        self.generate_alert(
            'CIRCUIT_BREAKER',
            RiskLevel.CRITICAL,
            f'熔断机制已激活: {reason}',
            1.0,
            0.0
        )
        logger.critical(f"熔断机制已激活: {reason}")
    
    def deactivate_circuit_breaker(self):
        """解除熔断"""
        self._circuit_breaker_active = False
        logger.info("熔断机制已解除")
    
    def _check_risk_system(self) -> Dict:
        """检查风控系统健康状态"""
        return {
            'status': HealthStatus.HEALTHY,
            'message': '风控系统运行正常',
            'metadata': {
                'circuit_breaker_active': self._circuit_breaker_active,
                'alert_count': len(self._alert_history),
                'rules_count': len(self._risk_rules)
            }
        }
    
    def get_alert_history(self, limit: int = 100) -> List[RiskAlert]:
        """获取告警历史"""
        return self._alert_history[-limit:]


# 导入HealthStatus
from .health_monitor import HealthStatus
