#!/bin/bash
# 揽宝智能投研交易平台 - Docker 入口脚本

# 加载 ROS2 环境
source /opt/ros/humble/setup.bash

# 加载工作空间（如果 install 存在）
if [ -f /workspace/install/setup.bash ]; then
    source /workspace/install/setup.bash
fi

# 设置 PYTHONPATH（兼容开发模式挂载）
export PYTHONPATH="/workspace/src:/workspace/install:${PYTHONPATH}"

# 设置 LD_LIBRARY_PATH（确保 ROS2 自定义消息库可被加载）
if [ -d /workspace/install/lanbao_interfaces/lib ]; then
    export LD_LIBRARY_PATH="/workspace/install/lanbao_interfaces/lib:${LD_LIBRARY_PATH}"
fi

# 执行传入的命令
exec "$@"
