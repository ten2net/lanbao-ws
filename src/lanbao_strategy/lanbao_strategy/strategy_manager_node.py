"""
策略管理器ROS2节点
"""
import rclpy
from loguru import logger
import json

from lanbao_core import LanBaoBaseNode, NodeConfig
from lanbao_interfaces.msg import StrategyStatus
from lanbao_interfaces.srv import ManageStrategy
from lanbao_interfaces.action import DeployStrategy
from rclpy.action import ActionServer

from .strategy_manager import StrategyManager
from .strategy_factory import StrategyFactory


class StrategyManagerNode(LanBaoBaseNode):
    """
    策略管理器节点
    
    职责:
    - 管理策略生命周期
    - 策略部署和回滚
    - 策略状态监控
    """
    
    def __init__(self):
        config = NodeConfig(
            node_name='strategy_manager_node',
            node_type='strategy_manager',
            publish_rate=0.2
        )
        super().__init__('strategy_manager_node', config)
        
        # 策略管理组件
        self._manager = StrategyManager()
        self._factory = StrategyFactory()
        
        # 策略状态发布（注意：基类已创建 _status_publisher 用于 NodeStatus）
        self._strategy_status_publisher = None
        
    def initialize(self) -> bool:
        """初始化节点"""
        try:
            # 创建策略状态发布器（与基类的 NodeStatus 发布器分离）
            self._strategy_status_publisher = self.create_publisher(
                StrategyStatus,
                'strategy/status',
                10
            )
            
            # 设置服务
            self._setup_services()
            
            # 设置动作服务器
            self._setup_action_server()
            
            # 策略状态更新定时器
            self._strategy_status_timer = self.create_timer(
                5.0,
                self._publish_strategies_status,
                callback_group=self._callback_group
            )
            
            logger.info("策略管理器节点初始化完成")
            return True
            
        except Exception as e:
            logger.exception(f"策略管理器节点初始化失败: {e}")
            return False
    
    def _setup_services(self):
        """设置ROS2服务"""
        # 策略管理服务
        self._manage_service = self.create_service(
            ManageStrategy,
            'strategy/manage',
            self._handle_manage_strategy,
            callback_group=self._callback_group
        )
        
        logger.info("策略管理服务已设置")
    
    def _setup_action_server(self):
        """设置动作服务器"""
        self._deploy_action_server = ActionServer(
            self,
            DeployStrategy,
            'strategy/deploy',
            self._execute_deploy_action,
            callback_group=self._callback_group
        )
        
        logger.info("策略部署动作服务器已设置")
    
    def _handle_manage_strategy(self, request, response):
        """
        处理策略管理请求
        """
        try:
            action = request.action
            strategy_id = request.strategy_id
            
            logger.info(f"收到策略管理请求: {action} {strategy_id}")
            
            if action == 'CREATE':
                # 解析配置
                config = json.loads(request.strategy_config) if request.strategy_config else {}
                template_id = config.get('template_id', 'ma_cross')
                name = config.get('name', f"strategy_{strategy_id}")
                params = config.get('params', {})
                
                # 创建策略
                strategy = self._factory.create_strategy(
                    template_id, strategy_id, name, params
                )
                
                if strategy:
                    self._manager.register(strategy)
                    response.success = True
                    response.message = f"策略 {strategy_id} 创建成功"
                else:
                    response.success = False
                    response.message = f"策略 {strategy_id} 创建失败"
                    
            elif action == 'START':
                if self._manager.start(strategy_id):
                    response.success = True
                    response.message = f"策略 {strategy_id} 已启动"
                else:
                    response.success = False
                    response.message = f"策略 {strategy_id} 启动失败"
                    
            elif action == 'STOP':
                if self._manager.stop(strategy_id):
                    response.success = True
                    response.message = f"策略 {strategy_id} 已停止"
                else:
                    response.success = False
                    response.message = f"策略 {strategy_id} 停止失败"
                    
            elif action == 'PAUSE':
                if self._manager.pause(strategy_id):
                    response.success = True
                    response.message = f"策略 {strategy_id} 已暂停"
                else:
                    response.success = False
                    response.message = f"策略 {strategy_id} 暂停失败"
                    
            elif action == 'RESUME':
                if self._manager.resume(strategy_id):
                    response.success = True
                    response.message = f"策略 {strategy_id} 已恢复"
                else:
                    response.success = False
                    response.message = f"策略 {strategy_id} 恢复失败"
                    
            elif action == 'DELETE':
                if self._manager.unregister(strategy_id):
                    response.success = True
                    response.message = f"策略 {strategy_id} 已删除"
                else:
                    response.success = False
                    response.message = f"策略 {strategy_id} 删除失败"
            else:
                response.success = False
                response.message = f"未知操作: {action}"
                
        except Exception as e:
            logger.exception(f"处理策略管理请求失败: {e}")
            response.success = False
            response.message = f"处理失败: {str(e)}"
        
        return response
    
    def _execute_deploy_action(self, goal_handle):
        """
        执行策略部署动作
        """
        goal = goal_handle.request
        strategy_id = goal.strategy_id
        deploy_mode = goal.deploy_mode
        
        logger.info(f"开始部署策略: {strategy_id} 模式: {deploy_mode}")
        
        feedback_msg = DeployStrategy.Feedback()
        result_msg = DeployStrategy.Result()
        
        try:
            # 发布进度
            feedback_msg.status = "验证策略"
            feedback_msg.progress = 0.1
            goal_handle.publish_feedback(feedback_msg)
            
            strategy = self._manager.get_strategy(strategy_id)
            if not strategy:
                result_msg.success = False
                result_msg.message = f"策略不存在: {strategy_id}"
                goal_handle.abort()
                return result_msg
            
            # 发布进度
            feedback_msg.status = "启动策略"
            feedback_msg.progress = 0.5
            goal_handle.publish_feedback(feedback_msg)
            
            # 启动策略
            if deploy_mode == 'SIMULATION':
                # 模拟模式
                self._manager.start(strategy_id)
                feedback_msg.status = "模拟运行中"
                feedback_msg.progress = 0.8
                goal_handle.publish_feedback(feedback_msg)
                
            elif deploy_mode == 'LIVE':
                # 实盘模式 (MVP版本不支持)
                result_msg.success = False
                result_msg.message = "MVP版本不支持实盘模式"
                goal_handle.abort()
                return result_msg
            
            # 发布进度
            feedback_msg.status = "部署完成"
            feedback_msg.progress = 1.0
            goal_handle.publish_feedback(feedback_msg)
            
            result_msg.success = True
            result_msg.message = f"策略 {strategy_id} 部署成功，模式: {deploy_mode}"
            goal_handle.succeed()
            
        except Exception as e:
            logger.exception(f"策略部署失败: {e}")
            result_msg.success = False
            result_msg.message = f"部署失败: {str(e)}"
            goal_handle.abort()
        
        return result_msg
    
    def _publish_strategies_status(self):
        """发布策略状态"""
        try:
            for strategy_id, strategy in self._manager.get_all_strategies().items():
                msg = StrategyStatus()
                msg.header.stamp = self.get_clock().now().to_msg()
                msg.strategy_id = strategy_id
                msg.strategy_name = strategy.name
                msg.state = strategy.state
                
                info = strategy.get_info()
                msg.performance = float(info.get('performance', 0))
                
                self._strategy_status_publisher.publish(msg)
                
        except Exception as e:
            logger.error(f"发布策略状态失败: {e}")
    
    def start(self) -> bool:
        """启动节点"""
        logger.info("策略管理器节点启动完成")
        return True
    
    def stop(self):
        """停止节点"""
        # 停止所有策略
        for strategy_id in list(self._manager.get_all_strategies().keys()):
            self._manager.stop(strategy_id)
        
        logger.info("策略管理器节点已停止")


def main(args=None):
    """节点入口函数"""
    rclpy.init(args=args)
    
    node = StrategyManagerNode()
    
    try:
        node.run()
    except KeyboardInterrupt:
        logger.info("收到中断信号")
    finally:
        node.shutdown()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
