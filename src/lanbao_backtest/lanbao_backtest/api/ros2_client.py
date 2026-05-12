"""ROS2 客户端管理器 — 单例模式，管理 rclpy 生命周期和 Service/Action 调用"""
import threading
from typing import Any, Dict, Optional

from loguru import logger


class ROS2ClientManager:
    """ROS2 客户端管理器（单例）

    职责：
    - 维护 rclpy 上下文生命周期
    - 管理 Service/Action 客户端
    - 处理连接断开重连
    """

    _instance: Optional["ROS2ClientManager"] = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, "_initialized"):
            return
        self._initialized = True

        self._node = None
        self._executor = None
        self._executor_thread = None
        self._connected = False
        self._clients: Dict[str, Any] = {}
        self._action_clients: Dict[str, Any] = {}

    def connect(self) -> bool:
        """初始化 ROS2 连接"""
        if self._connected:
            return True

        try:
            import rclpy
            from rclpy.executors import MultiThreadedExecutor

            if not rclpy.ok():
                rclpy.init()

            self._node = rclpy.create_node("lanbao_backtest_api")
            self._executor = MultiThreadedExecutor()
            self._executor.add_node(self._node)

            self._executor_thread = threading.Thread(
                target=self._executor.spin, daemon=True
            )
            self._executor_thread.start()

            self._connected = True
            logger.info("ROS2 Client Manager 已连接")
            return True

        except Exception as e:
            logger.error(f"ROS2 连接失败: {e}")
            return False

    def disconnect(self) -> None:
        """断开 ROS2 连接"""
        if not self._connected:
            return

        try:
            import rclpy

            if self._executor:
                self._executor.shutdown()
            if self._node:
                self._node.destroy_node()
            if rclpy.ok():
                rclpy.shutdown()

            self._connected = False
            logger.info("ROS2 Client Manager 已断开")

        except Exception as e:
            logger.error(f"ROS2 断开失败: {e}")

    def get_service_client(self, service_type: Any, service_name: str) -> Any:
        """获取或创建 Service 客户端"""
        key = f"service:{service_name}"
        if key not in self._clients:
            client = self._node.create_client(service_type, service_name)
            self._clients[key] = client
        return self._clients[key]

    def get_action_client(self, action_type: Any, action_name: str) -> Any:
        """获取或创建 Action 客户端"""
        key = f"action:{action_name}"
        if key not in self._action_clients:
            from rclpy.action import ActionClient

            client = ActionClient(self._node, action_type, action_name)
            self._action_clients[key] = client
        return self._action_clients[key]

    @property
    def is_connected(self) -> bool:
        return self._connected

    @property
    def node(self) -> Any:
        return self._node


# 便捷函数

def get_ros2_manager() -> ROS2ClientManager:
    return ROS2ClientManager()
