"""
揽宝智能投研交易平台 - 核心启动文件
"""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, LogInfo
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    """生成启动描述"""

    # 声明启动参数
    log_level_arg = DeclareLaunchArgument(
        'log_level',
        default_value='info',
        description='日志级别 (debug, info, warn, error)'
    )

    log_level = LaunchConfiguration('log_level')

    return LaunchDescription([
        log_level_arg,

        LogInfo(msg='启动揽宝智能投研平台核心服务...'),

        # 核心协调节点
        Node(
            package='lanbao_core',
            executable='core_node',
            name='lanbao_core',
            output='screen',
            parameters=[{'log_level': log_level}]
        ),

        LogInfo(msg='揽宝核心服务启动完成'),
    ])
