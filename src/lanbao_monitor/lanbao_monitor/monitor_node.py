"""
监控ROS2节点
"""
import rclpy
import psutil
from datetime import datetime
from loguru import logger

from lanbao_core import LanBaoBaseNode, NodeConfig
from lanbao_interfaces.msg import NodeStatus, SystemAlert
from lanbao_interfaces.srv import GetNodeStatus


class MonitorNode(LanBaoBaseNode):
    """
    监控节点
    
    职责:
    - 系统资源监控
    - 节点状态收集
    - 告警生成
    """
    
    def __init__(self):
        config = NodeConfig(
            node_name='monitor_node',
            node_type='monitor',
            publish_rate=0.1
        )
        super().__init__('monitor_node', config)
        
        # 节点状态缓存
        self._node_statuses: dict = {}
        
        # 告警历史
        self._alerts: list = []
        
        # 订阅器
        self._status_subscription = None
        self._alert_subscription = None
        
    def initialize(self) -> bool:
        """初始化节点"""
        try:
            # 订阅节点状态
            self._status_subscription = self.create_subscription(
                NodeStatus,
                '/node_status',
                self._on_node_status,
                10
            )
            
            # 订阅系统告警
            self._alert_subscription = self.create_subscription(
                SystemAlert,
                '/system/alerts',
                self._on_system_alert,
                10
            )
            
            # 设置服务
            self._setup_services()
            
            # 系统监控定时器
            self._monitor_timer = self.create_timer(
                10.0,  # 每10秒检查一次
                self._monitor_system,
                callback_group=self._callback_group
            )
            
            logger.info("监控节点初始化完成")
            return True
            
        except Exception as e:
            logger.exception(f"监控节点初始化失败: {e}")
            return False
    
    def _setup_services(self):
        """设置ROS2服务"""
        # 获取节点状态服务
        self._get_status_service = self.create_service(
            GetNodeStatus,
            'monitor/nodes',
            self._handle_get_node_status,
            callback_group=self._callback_group
        )
        
        logger.info("监控服务已设置")
    
    def _on_node_status(self, msg: NodeStatus):
        """接收节点状态"""
        self._node_statuses[msg.node_name] = {
            'node_type': msg.node_type,
            'status': msg.status,
            'cpu_usage': msg.cpu_usage,
            'memory_usage': msg.memory_usage,
            'timestamp': msg.timestamp
        }
    
    def _on_system_alert(self, msg: SystemAlert):
        """接收系统告警"""
        self._alerts.append({
            'type': msg.alert_type,
            'component': msg.component,
            'message': msg.message,
            'timestamp': msg.timestamp
        })
        
        # 限制历史记录大小
        if len(self._alerts) > 1000:
            self._alerts = self._alerts[-1000:]
        
        logger.warning(f"[系统告警] [{msg.alert_type}] {msg.component}: {msg.message}")
    
    def _handle_get_node_status(self, request, response):
        """
        处理获取节点状态请求
        """
        try:
            node_name = request.node_name
            
            if node_name:
                # 获取指定节点状态
                status = self._node_statuses.get(node_name)
                if status:
                    msg = NodeStatus()
                    msg.node_name = node_name
                    msg.node_type = status['node_type']
                    msg.status = status['status']
                    msg.cpu_usage = status['cpu_usage']
                    msg.memory_usage = status['memory_usage']
                    response.statuses = [msg]
                else:
                    response.statuses = []
            else:
                # 获取所有节点状态
                response.statuses = []
                for name, status in self._node_statuses.items():
                    msg = NodeStatus()
                    msg.node_name = name
                    msg.node_type = status['node_type']
                    msg.status = status['status']
                    msg.cpu_usage = status['cpu_usage']
                    msg.memory_usage = status['memory_usage']
                    response.statuses.append(msg)
            
            response.success = True
            
        except Exception as e:
            logger.error(f"获取节点状态失败: {e}")
            response.success = False
        
        return response
    
    def _monitor_system(self):
        """监控系统资源"""
        try:
            # CPU使用率
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # 内存使用
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            
            # 磁盘使用
            disk = psutil.disk_usage('/')
            disk_percent = disk.percent
            
            # 检查告警条件
            if cpu_percent > 80:
                self._publish_alert('WARNING', f'CPU使用率高: {cpu_percent}%', 'system')
            
            if memory_percent > 85:
                self._publish_alert('WARNING', f'内存使用率高: {memory_percent}%', 'system')
            
            if disk_percent > 90:
                self._publish_alert('CRITICAL', f'磁盘空间不足: {disk_percent}%', 'system')
            
            # 更新自身状态
            self._status.cpu_usage = cpu_percent
            self._status.memory_usage = memory_percent
            
            logger.debug(f"系统状态 - CPU: {cpu_percent}%, 内存: {memory_percent}%, 磁盘: {disk_percent}%")
            
        except Exception as e:
            logger.error(f"系统监控失败: {e}")
    
    def start(self) -> bool:
        """启动节点"""
        logger.info("监控节点启动完成")
        return True
    
    def stop(self):
        """停止节点"""
        logger.info("监控节点已停止")


def main(args=None):
    """节点入口函数"""
    rclpy.init(args=args)
    
    node = MonitorNode()
    
    try:
        node.run()
    except KeyboardInterrupt:
        logger.info("收到中断信号")
    finally:
        node.shutdown()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
