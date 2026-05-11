"""
系统指标采集节点

使用 psutil 采集系统级指标，定时发布到 /system/metrics Topic。
"""
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile

import psutil
from loguru import logger

from lanbao_interfaces.msg import SystemMetrics


class SystemMetricsNode(Node):
    """
    系统指标采集节点

    职责:
    - 定时采集 CPU、内存、磁盘、网络、负载等指标
    - 发布 SystemMetrics 消息到 /system/metrics
    """

    def __init__(self):
        super().__init__('system_metrics_node')

        # 创建 Publisher
        qos = QoSProfile(depth=10)
        self._publisher = self.create_publisher(
            SystemMetrics,
            '/system/metrics',
            qos
        )

        # 创建定时器，每 5 秒采集一次
        self._timer = self.create_timer(5.0, self._publish_metrics)

        logger.info("system_metrics_node 初始化完成")

    def _publish_metrics(self):
        """采集并发布系统指标"""
        msg = SystemMetrics()
        msg.timestamp = self.get_clock().now().to_msg()

        try:
            msg.cpu_percent = float(psutil.cpu_percent(interval=None))
        except Exception as e:
            self.get_logger().warning(f"采集 CPU 指标失败: {e}")
            msg.cpu_percent = 0.0

        try:
            msg.memory_percent = float(psutil.virtual_memory().percent)
        except Exception as e:
            self.get_logger().warning(f"采集内存指标失败: {e}")
            msg.memory_percent = 0.0

        try:
            msg.disk_percent = float(psutil.disk_usage('/').percent)
        except Exception as e:
            self.get_logger().warning(f"采集磁盘指标失败: {e}")
            msg.disk_percent = 0.0

        try:
            net_io = psutil.net_io_counters()
            msg.network_bytes_sent = int(net_io.bytes_sent)
            msg.network_bytes_recv = int(net_io.bytes_recv)
        except Exception as e:
            self.get_logger().warning(f"采集网络指标失败: {e}")
            msg.network_bytes_sent = 0
            msg.network_bytes_recv = 0

        try:
            msg.load_average_1m = float(psutil.getloadavg()[0])
        except Exception as e:
            self.get_logger().warning(f"采集负载指标失败: {e}")
            msg.load_average_1m = 0.0

        self._publisher.publish(msg)
        logger.debug(
            f"系统指标已发布 - CPU: {msg.cpu_percent:.1f}%, "
            f"内存: {msg.memory_percent:.1f}%, 磁盘: {msg.disk_percent:.1f}%"
        )


def main(args=None):
    """节点入口函数"""
    rclpy.init(args=args)
    node = SystemMetricsNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        logger.info("收到中断信号，节点退出")
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
