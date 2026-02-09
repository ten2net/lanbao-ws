"""
揽宝系统ROS2节点基类
实现统一的节点生命周期管理和通信机制
"""
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy, DurabilityPolicy
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import MultiThreadedExecutor
import threading
import time
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, Callable
from loguru import logger

from lanbao_interfaces.msg import NodeStatus, SystemAlert
from .config import NodeConfig
from .metrics import MetricsCollector
from .health_monitor import HealthMonitor, HealthStatus


class LanBaoBaseNode(ABC, Node):
    """
    揽宝系统节点基类
    
    提供统一的功能:
    - 节点生命周期管理
    - 健康监控
    - 指标收集
    - 配置管理
    - 错误处理和重试机制
    """
    
    def __init__(self, node_name: str, config: Optional[NodeConfig] = None):
        """
        初始化节点
        
        Args:
            node_name: 节点名称
            config: 节点配置，如果为None则从环境变量加载
        """
        # 初始化配置
        self._node_config = config or NodeConfig.from_env()
        self._node_config.node_name = node_name
        
        # 初始化ROS2节点
        super().__init__(node_name)
        
        # 初始化组件
        self._metrics = MetricsCollector(node_name)
        self._health = HealthMonitor(node_name)
        self._callback_group = ReentrantCallbackGroup()
        
        # 节点状态
        self._status = NodeStatus()
        self._status.node_name = node_name
        self._status.node_type = self._node_config.node_type
        self._status.status = "INITIALIZING"
        
        # 运行状态
        self._running = False
        self._shutdown_event = threading.Event()
        
        # QoS配置
        self._qos_profiles = self._setup_qos_profiles()
        
        # 状态发布
        self._status_publisher = self.create_publisher(
            NodeStatus,
            f'{node_name}/status',
            self._qos_profiles['status']
        )
        
        # 告警发布
        self._alert_publisher = self.create_publisher(
            SystemAlert,
            '/system/alerts',
            self._qos_profiles['alert']
        )
        
        # 状态发布定时器
        self._status_timer = self.create_timer(
            5.0,  # 每5秒发布一次状态
            self._publish_status
        )
        
        logger.info(f"节点 [{node_name}] 初始化完成")
    
    def _setup_qos_profiles(self) -> Dict[str, QoSProfile]:
        """设置QoS配置文件"""
        return {
            'default': QoSProfile(
                reliability=ReliabilityPolicy.RELIABLE,
                history=HistoryPolicy.KEEP_LAST,
                depth=10
            ),
            'sensor': QoSProfile(
                reliability=ReliabilityPolicy.BEST_EFFORT,
                history=HistoryPolicy.KEEP_LAST,
                depth=100
            ),
            'status': QoSProfile(
                reliability=ReliabilityPolicy.RELIABLE,
                history=HistoryPolicy.KEEP_LAST,
                depth=1
            ),
            'alert': QoSProfile(
                reliability=ReliabilityPolicy.RELIABLE,
                history=HistoryPolicy.KEEP_ALL,
                durability=DurabilityPolicy.TRANSIENT_LOCAL
            )
        }
    
    @abstractmethod
    def initialize(self) -> bool:
        """
        初始化节点
        子类必须实现此方法
        
        Returns:
            bool: 初始化是否成功
        """
        pass
    
    @abstractmethod
    def start(self) -> bool:
        """
        启动节点
        子类必须实现此方法
        
        Returns:
            bool: 启动是否成功
        """
        pass
    
    @abstractmethod
    def stop(self):
        """
        停止节点
        子类必须实现此方法
        """
        pass
    
    def run(self):
        """
        运行节点的主循环
        """
        try:
            # 初始化
            if not self.initialize():
                logger.error(f"节点 [{self.get_name()}] 初始化失败")
                self._status.status = "ERROR"
                return
            
            # 启动
            if not self.start():
                logger.error(f"节点 [{self.get_name()}] 启动失败")
                self._status.status = "ERROR"
                return
            
            self._running = True
            self._status.status = "RUNNING"
            
            # 启动健康监控
            self._health.start_monitoring()
            
            logger.info(f"节点 [{self.get_name()}] 运行中...")
            
            # 等待关闭信号
            while self._running and not self._shutdown_event.is_set():
                self._main_loop()
                time.sleep(0.01)  # 10ms间隔
                
        except Exception as e:
            logger.exception(f"节点 [{self.get_name()}] 运行异常: {e}")
            self._status.status = "ERROR"
            self._publish_alert("ERROR", f"节点运行异常: {str(e)}")
        finally:
            self.shutdown()
    
    def _main_loop(self):
        """
        主循环 - 子类可覆盖以实现自定义逻辑
        """
        pass
    
    def shutdown(self):
        """
        关闭节点
        """
        logger.info(f"节点 [{self.get_name()}] 正在关闭...")
        
        self._running = False
        self._shutdown_event.set()
        
        # 停止健康监控
        self._health.stop_monitoring()
        
        # 调用子类的停止方法
        try:
            self.stop()
        except Exception as e:
            logger.error(f"节点 [{self.get_name()}] 停止时出错: {e}")
        
        # 更新状态
        self._status.status = "STOPPED"
        self._publish_status()
        
        # 销毁ROS2资源
        self.destroy_timer(self._status_timer)
        self.destroy_publisher(self._status_publisher)
        self.destroy_publisher(self._alert_publisher)
        
        logger.info(f"节点 [{self.get_name()}] 已关闭")
    
    def _publish_status(self):
        """发布节点状态"""
        try:
            self._status.timestamp = self.get_clock().now().to_msg()
            self._status_publisher.publish(self._status)
            self._metrics.increment_counter('status_published')
        except Exception as e:
            logger.error(f"发布状态失败: {e}")
    
    def _publish_alert(self, alert_type: str, message: str, component: str = None):
        """
        发布系统告警
        
        Args:
            alert_type: 告警类型 (INFO, WARNING, ERROR, CRITICAL)
            message: 告警消息
            component: 组件名称，默认为节点名
        """
        try:
            alert = SystemAlert()
            alert.header.stamp = self.get_clock().now().to_msg()
            alert.alert_type = alert_type
            alert.component = component or self.get_name()
            alert.message = message
            alert.timestamp = int(time.time() * 1000)
            
            self._alert_publisher.publish(alert)
            logger.warning(f"[{alert_type}] {message}")
            
        except Exception as e:
            logger.error(f"发布告警失败: {e}")
    
    def get_status(self) -> NodeStatus:
        """获取节点状态"""
        return self._status
    
    def get_metrics(self) -> MetricsCollector:
        """获取指标收集器"""
        return self._metrics
    
    def get_health(self) -> HealthMonitor:
        """获取健康监控器"""
        return self._health
    
    def is_running(self) -> bool:
        """检查节点是否正在运行"""
        return self._running
    
    def publish_with_retry(self, publisher, message, max_retries: int = None) -> bool:
        """
        带重试机制的发布
        
        Args:
            publisher: ROS2发布器
            message: 要发布的消息
            max_retries: 最大重试次数，默认使用配置值
            
        Returns:
            bool: 发布是否成功
        """
        max_retries = max_retries or self._node_config.retry_count
        
        for attempt in range(max_retries + 1):
            try:
                publisher.publish(message)
                return True
            except Exception as e:
                if attempt < max_retries:
                    logger.warning(f"发布失败，重试 {attempt + 1}/{max_retries}: {e}")
                    time.sleep(0.1 * (attempt + 1))  # 指数退避
                else:
                    logger.error(f"发布失败，已达到最大重试次数: {e}")
                    return False
        
        return False
    
    def call_service_with_timeout(self, client, request, timeout_sec: float = None) -> Optional[Any]:
        """
        带超时的服务调用
        
        Args:
            client: ROS2服务客户端
            request: 服务请求
            timeout_sec: 超时时间(秒)，默认使用配置值
            
        Returns:
            服务响应，超时返回None
        """
        timeout_sec = timeout_sec or (self._node_config.timeout_ms / 1000.0)
        
        try:
            future = client.call_async(request)
            rclpy.spin_until_future_complete(self, future, timeout_sec=timeout_sec)
            
            if future.done():
                return future.result()
            else:
                logger.warning(f"服务调用超时 ({timeout_sec}s)")
                return None
                
        except Exception as e:
            logger.error(f"服务调用失败: {e}")
            return None
