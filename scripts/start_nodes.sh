#!/bin/bash
# 揽宝系统节点启动脚本

# 设置颜色
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}=======================================${NC}"
echo -e "${BLUE}  揽宝智能投研交易平台 - 节点启动器   ${NC}"
echo -e "${BLUE}=======================================${NC}"

# 加载ROS2环境
source /opt/ros/humble/setup.bash

# 加载工作空间
if [ -f "./install/setup.bash" ]; then
    source ./install/setup.bash
    echo -e "${GREEN}✓ 工作空间已加载${NC}"
else
    echo -e "${YELLOW}⚠ 未找到install目录，请先运行 colcon build${NC}"
    exit 1
fi

# 创建日志目录
mkdir -p logs

# 启动函数
start_node() {
    local node_name=$1
    local package=$2
    local executable=$3
    
    echo -e "${BLUE}启动 $node_name...${NC}"
    ros2 run $package $executable > "logs/${node_name}.log" 2>&1 &
    echo $! > "logs/${node_name}.pid"
    echo -e "${GREEN}✓ $node_name 已启动 (PID: $!)${NC}"
}

# 启动所有节点
echo ""
echo "正在启动节点..."

# 1. 市场数据节点
start_node "market_data" "lanbao_data" "market_data_node"
sleep 2

# 2. 回测引擎节点
start_node "backtest" "lanbao_backtest" "backtest_engine_node"
sleep 1

# 3. 策略管理节点
start_node "strategy" "lanbao_strategy" "strategy_manager_node"
sleep 1

# 4. 风险控制节点
start_node "risk" "lanbao_risk" "risk_control_node"
sleep 1

# 5. 监控节点
start_node "monitor" "lanbao_monitor" "monitor_node"

echo ""
echo -e "${GREEN}=======================================${NC}"
echo -e "${GREEN}  所有节点已启动                      ${NC}"
echo -e "${GREEN}=======================================${NC}"
echo ""
echo "使用以下命令查看日志:"
echo "  tail -f logs/market_data.log"
echo "  tail -f logs/backtest.log"
echo "  tail -f logs/strategy.log"
echo ""
echo "使用以下命令停止所有节点:"
echo "  ./scripts/stop_nodes.sh"
