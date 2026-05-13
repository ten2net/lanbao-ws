#!/bin/bash
# 揽宝系统构建脚本

echo "======================================="
echo "  揽宝智能投研交易平台 - 构建脚本     "
echo "======================================="

# 加载ROS2环境
source /opt/ros/humble/setup.bash

echo ""
echo "正在构建揽宝系统..."

# 构建
colcon build --packages-select \
    lanbao_interfaces \
    lanbao_core \
    lanbao_data \
    lanbao_strategy \
    lanbao_backtest \
    lanbao_risk \
    lanbao_monitor \
    lanbao_ai_research \
    --symlink-install

if [ $? -eq 0 ]; then
    echo ""
    echo "======================================="
    echo "  构建成功!                          "
    echo "======================================="
    echo ""
    echo "使用以下命令启动系统:"
    echo "  source install/setup.bash"
    echo "  ./scripts/start_nodes.sh"
else
    echo ""
    echo "======================================="
    echo "  构建失败，请检查错误信息            "
    echo "======================================="
    exit 1
fi
