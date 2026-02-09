"""
风险控制ROS2节点
"""
import rclpy
from loguru import logger
from typing import Dict, Any

from lanbao_core import RiskControlNode as BaseRiskNode, NodeConfig
from lanbao_core.risk_node import RiskLimits, RiskLevel
from lanbao_interfaces.msg import RiskAlert, TradeSignal, PortfolioStatus
from lanbao_interfaces.srv import CheckRisk


class RiskControlNode(BaseRiskNode):
    """
    风险控制节点
    
    职责:
    - 实时风险监控
    - 交易前风险检查
    - 熔断机制管理
    """
    
    def __init__(self):
        config = NodeConfig(
            node_name='risk_control_node',
            node_type='risk_control',
            parameters={
                'risk_limits': {
                    'max_position_size': 0.2,
                    'max_drawdown': 0.1,
                    'max_daily_loss': 0.05
                }
            }
        )
        super().__init__('risk_control_node', config)
        
        self._daily_pnl = 0.0
        self._daily_trades = 0
        
    def _setup_risk_rules(self):
        """设置风险规则"""
        # MVP版本使用基础风险规则
        self._risk_rules = [
            'position_limit',
            'drawdown_limit',
            'daily_loss_limit'
        ]
        logger.info("风险规则已设置")
    
    def initialize(self) -> bool:
        """初始化节点"""
        try:
            if not super().initialize():
                return False
            
            # 设置服务
            self._setup_services()
            
            logger.info("风险控制节点初始化完成")
            return True
            
        except Exception as e:
            logger.exception(f"风险控制节点初始化失败: {e}")
            return False
    
    def _setup_services(self):
        """设置ROS2服务"""
        # 风险检查服务
        self._check_risk_service = self.create_service(
            CheckRisk,
            'risk/check',
            self._handle_check_risk,
            callback_group=self._callback_group
        )
        
        logger.info("风险检查服务已设置")
    
    def _handle_check_risk(self, request, response):
        """
        处理风险检查请求
        """
        try:
            signal = request.signal
            portfolio = request.portfolio
            
            logger.debug(f"风险检查: {signal.symbol} {signal.action}")
            
            # 执行风险检查
            result = self.check_risk(signal, portfolio)
            
            response.approved = result.get('approved', False)
            response.reason = result.get('reason', '')
            response.risk_score = result.get('risk_score', 0.0)
            
        except Exception as e:
            logger.error(f"风险检查失败: {e}")
            response.approved = False
            response.reason = f"检查失败: {str(e)}"
            response.risk_score = 1.0
        
        return response
    
    def check_risk(self, signal: TradeSignal, 
                   portfolio: PortfolioStatus) -> Dict[str, Any]:
        """
        检查交易风险
        
        Args:
            signal: 交易信号
            portfolio: 当前持仓
            
        Returns:
            风险检查结果
        """
        # 熔断检查
        if self._circuit_breaker_active:
            return {
                'approved': False,
                'reason': '熔断机制已激活',
                'risk_score': 1.0
            }
        
        risk_score = 0.0
        reasons = []
        
        # 检查回撤
        if abs(portfolio.drawdown) > self._risk_limits.max_drawdown:
            risk_score += 0.4
            reasons.append(f"回撤超限: {portfolio.drawdown:.2%}")
        
        # 检查日亏损
        if portfolio.day_pnl < -portfolio.total_value * self._risk_limits.max_daily_loss:
            risk_score += 0.3
            reasons.append(f"日亏损超限: {portfolio.day_pnl:.2f}")
        
        # 检查仓位 (简化处理)
        if signal.action == 'BUY':
            trade_value = signal.quantity * signal.price
            position_ratio = trade_value / portfolio.total_value if portfolio.total_value > 0 else 1
            
            if position_ratio > self._risk_limits.max_position_size:
                risk_score += 0.3
                reasons.append(f"仓位超限: {position_ratio:.2%}")
        
        # 综合评估
        approved = risk_score < 0.7
        
        return {
            'approved': approved,
            'reason': '; '.join(reasons) if reasons else '风险检查通过',
            'risk_score': risk_score
        }
    
    def start(self) -> bool:
        """启动节点"""
        logger.info("风险控制节点启动完成")
        return True
    
    def stop(self):
        """停止节点"""
        logger.info("风险控制节点已停止")


def main(args=None):
    """节点入口函数"""
    rclpy.init(args=args)
    
    node = RiskControlNode()
    
    try:
        node.run()
    except KeyboardInterrupt:
        logger.info("收到中断信号")
    finally:
        node.shutdown()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
