"""
揽宝核心节点 - 系统协调服务
"""
import rclpy
from rclpy.node import Node
from std_msgs.msg import String


class CoreNode(Node):
    """核心协调节点"""
    
    def __init__(self):
        super().__init__('lanbao_core')
        self.get_logger().info('揽宝核心节点已启动')
        
        # 创建状态发布器
        self.status_pub = self.create_publisher(String, '/lanbao/system_status', 10)
        
        # 定时发布状态
        self.timer = self.create_timer(5.0, self.publish_status)
    
    def publish_status(self):
        """发布系统状态"""
        msg = String()
        msg.data = 'System running normally'
        self.status_pub.publish(msg)
        self.get_logger().debug('系统状态已发布')


def main(args=None):
    """主函数"""
    rclpy.init(args=args)
    node = CoreNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
