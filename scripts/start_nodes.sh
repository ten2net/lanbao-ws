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
LANBAO_INSTALL_PATHS="./install/lanbao_interfaces/lib/python3.10/site-packages:./install/lanbao_core/lib/python3.10/site-packages:./install/lanbao_data/lib/python3.10/site-packages:./install/lanbao_strategy/lib/python3.10/site-packages:./install/lanbao_backtest/lib/python3.10/site-packages:./install/lanbao_risk/lib/python3.10/site-packages:./install/lanbao_monitor/lib/python3.10/site-packages:./install/lanbao_ai_research/lib/python3.10/site-packages"
# build目录包含实际的包代码(.egg-link指向这里)
LANBAO_BUILD_PATHS="./build/lanbao_interfaces:./build/lanbao_core:./build/lanbao_data:./build/lanbao_strategy:./build/lanbao_backtest:./build/lanbao_risk:./build/lanbao_monitor:./build/lanbao_ai_research"

# 停止已运行的同名节点
stop_existing() {
    local node_name=$1
    local pids

    case "$node_name" in
        "market_data") pids=$(pgrep -f "lanbao_data\.market_data_node") ;;
        "data_sync") pids=$(pgrep -f "lanbao_data\.data_sync_node") ;;
        "backtest") pids=$(pgrep -f "lanbao_backtest\.backtest_engine_node") ;;
        "strategy") pids=$(pgrep -f "lanbao_strategy\.strategy_manager_node") ;;
        "risk") pids=$(pgrep -f "lanbao_risk\.risk_control_node") ;;
        "monitor") pids=$(pgrep -f "lanbao_monitor\.monitor_node") ;;
        "system_metrics") pids=$(pgrep -f "lanbao_monitor\.system_metrics_node") ;;
        "ai_research") pids=$(pgrep -f "lanbao_ai_research\.ai_research_node") ;;
        "rosbridge_server") pids=$(pgrep -f "rosbridge_websocket_launch") ;;
    esac

    if [ -n "$pids" ]; then
        echo -e "${YELLOW}  发现已运行的 $node_name，先停止旧进程...${NC}"
        for pid in $pids; do
            kill "$pid" 2>/dev/null
        done
        sleep 1
        # 强制清理仍未停止的
        for pid in $pids; do
            if kill -0 "$pid" 2>/dev/null; then
                kill -9 "$pid" 2>/dev/null
            fi
        done
    fi
}

# 启动函数
start_node() {
    local node_name=$1
    local package=$2
    local module=$3

    echo -e "${BLUE}启动 $node_name...${NC}"

    # 先停止已存在的同名节点
    stop_existing "$node_name"

    # 清理旧 pid 文件
    rm -f "logs/${node_name}.pid"

    # 创建启动脚本
    cat > "logs/${node_name}_launcher.sh" << EOF
#!/bin/bash
cd "\$(dirname "\$0")/.."
source /opt/ros/humble/setup.bash
source ./install/setup.bash
export PYTHONPATH="${ROS_PYTHONPATH}:${LANBAO_INSTALL_PATHS}:${LANBAO_BUILD_PATHS}"
export LD_LIBRARY_PATH=./install/lanbao_interfaces/lib:/opt/ros/humble/lib/x86_64-linux-gnu:/opt/ros/humble/lib:/usr/local/lib
export PATH=/opt/ros/humble/bin:\$PATH
exec ./.venv/bin/python -m ${module} 2>&1
EOF
    chmod +x "logs/${node_name}_launcher.sh"

    # 使用nohup启动
    nohup "logs/${node_name}_launcher.sh" > "logs/${node_name}.log" 2>&1 &

    echo $! > "logs/${node_name}.pid"
    echo -e "${GREEN}✓ $node_name 已启动 (PID: $!)${NC}"
}

# 启动 ROS2 WebSocket 桥接 (rosbridge_server)
start_rosbridge() {
    echo -e "${BLUE}启动 rosbridge_server (WebSocket: ws://localhost:9090)...${NC}"

    # 先停止已存在的 rosbridge
    stop_existing "rosbridge_server"
    rm -f "logs/rosbridge_server.pid"

    cat > "logs/rosbridge_launcher.sh" << 'EOF'
#!/bin/bash
cd "$(dirname "$0")/.."
source /opt/ros/humble/setup.bash
source ./install/setup.bash
export LD_LIBRARY_PATH=./install/lanbao_interfaces/lib:/opt/ros/humble/lib/x86_64-linux-gnu:/opt/ros/humble/lib:/usr/local/lib
export PATH=/opt/ros/humble/bin:$PATH
exec ros2 launch rosbridge_server rosbridge_websocket_launch.xml port:=9090 max_message_size:=10000000 2>&1
EOF
    chmod +x "logs/rosbridge_launcher.sh"

    nohup "logs/rosbridge_launcher.sh" > "logs/rosbridge_server.log" 2>&1 &

    echo $! > "logs/rosbridge_server.pid"
    echo -e "${GREEN}✓ rosbridge_server 已启动 (PID: $!)${NC}"
}

# 启动所有节点
echo ""
echo "正在启动节点..."

# 0. 启动 rosbridge_server (WebSocket 桥接)
start_rosbridge
sleep 2

# 1. 市场数据节点
start_node "market_data" "lanbao_data" "lanbao_data.market_data_node"
sleep 2

# 2. 数据同步节点
start_node "data_sync" "lanbao_data" "lanbao_data.data_sync_node"
sleep 1

# 3. 回测引擎节点
start_node "backtest" "lanbao_backtest" "lanbao_backtest.backtest_engine_node"
sleep 1

# 4. 策略管理节点
start_node "strategy" "lanbao_strategy" "lanbao_strategy.strategy_manager_node"
sleep 1

# 5. 风险控制节点
start_node "risk" "lanbao_risk" "lanbao_risk.risk_control_node"
sleep 1

# 6. 监控节点
start_node "monitor" "lanbao_monitor" "lanbao_monitor.monitor_node"
sleep 1

# 7. 系统指标节点
start_node "system_metrics" "lanbao_monitor" "lanbao_monitor.system_metrics_node"
sleep 1

# 8. AI 投研节点
start_node "ai_research" "lanbao_ai_research" "lanbao_ai_research.ai_research_node"

echo ""
echo -e "${GREEN}=======================================${NC}"
echo -e "${GREEN}  所有节点已启动                      ${NC}"
echo -e "${GREEN}=======================================${NC}"
echo ""
echo "使用以下命令查看日志:"
echo "  tail -f logs/market_data.log"
echo "  tail -f logs/backtest.log"
echo "  tail -f logs/strategy.log"
echo "  tail -f logs/system_metrics.log"
echo ""
echo "使用以下命令停止所有节点:"
echo "  ./scripts/stop_nodes.sh"
