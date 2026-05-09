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

# 基础PYTHONPATH (注意: lanbao_interfaces使用python3.11目录但包含python3.10的so文件)
ROS_PYTHONPATH="/opt/ros/humble/lib/python3.10/site-packages:/opt/ros/humble/local/lib/python3.10/dist-packages"
LANBAO_INSTALL_PATHS="./install/lanbao_interfaces/lib/python3.10/site-packages:./install/lanbao_core/lib/python3.10/site-packages:./install/lanbao_data/lib/python3.10/site-packages:./install/lanbao_strategy/lib/python3.10/site-packages:./install/lanbao_backtest/lib/python3.10/site-packages:./install/lanbao_risk/lib/python3.10/site-packages:./install/lanbao_monitor/lib/python3.10/site-packages"
# build目录包含实际的包代码(.egg-link指向这里)
LANBAO_BUILD_PATHS="./build/lanbao_interfaces:./build/lanbao_core:./build/lanbao_data:./build/lanbao_strategy:./build/lanbao_backtest:./build/lanbao_risk:./build/lanbao_monitor"

# 启动函数
start_node() {
    local node_name=$1
    local package=$2
    local module=$3
    
    echo -e "${BLUE}启动 $node_name...${NC}"
    
    # 创建启动脚本
    cat > "logs/${node_name}_launcher.sh" << EOF
#!/bin/bash
cd "\$(dirname "\$0")/.."
source /opt/ros/humble/setup.bash
source ./install/setup.bash
export PYTHONPATH="${ROS_PYTHONPATH}:${LANBAO_INSTALL_PATHS}:${LANBAO_BUILD_PATHS}"
export LD_LIBRARY_PATH=./install/lanbao_interfaces/lib:/opt/ros/humble/lib/x86_64-linux-gnu:/opt/ros/humble/lib:/usr/local/lib
export PATH=/opt/ros/humble/bin:\$PATH
./.venv/bin/python -m ${module} 2>&1
EOF
    chmod +x "logs/${node_name}_launcher.sh"
    
    # 使用nohup启动
    nohup "logs/${node_name}_launcher.sh" > "logs/${node_name}.log" 2>&1 &
    
    echo $! > "logs/${node_name}.pid"
    echo -e "${GREEN}✓ $node_name 已启动 (PID: $!)${NC}"
}

# 启动所有节点
echo ""
echo "正在启动节点..."

# 1. 市场数据节点
start_node "market_data" "lanbao_data" "lanbao_data.market_data_node"
sleep 2

# 2. 回测引擎节点
start_node "backtest" "lanbao_backtest" "lanbao_backtest.backtest_engine_node"
sleep 1

# 3. 策略管理节点
start_node "strategy" "lanbao_strategy" "lanbao_strategy.strategy_manager_node"
sleep 1

# 4. 风险控制节点
start_node "risk" "lanbao_risk" "lanbao_risk.risk_control_node"
sleep 1

# 5. 监控节点
start_node "monitor" "lanbao_monitor" "lanbao_monitor.monitor_node"

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
