#!/bin/bash
# 揽宝系统全量启动脚本（节点 + API + Web）

set -e

cd "$(dirname "$0")/.."

# 设置颜色
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${BLUE}=======================================${NC}"
echo -e "${BLUE}  揽宝智能投研交易平台 - 全量启动器   ${NC}"
echo -e "${BLUE}=======================================${NC}"

mkdir -p logs

# 1. 启动 ROS2 节点
echo ""
echo -e "${BLUE}[1/3] 启动 ROS2 节点...${NC}"
./scripts/start_nodes.sh

# 2. 启动 Backtest API（后台）
echo ""
echo -e "${BLUE}[2/3] 启动 Backtest API (port 8000)...${NC}"

# 先停止已存在的 API
api_pids=$(pgrep -f "uvicorn lanbao_backtest\.api\.main:app" || true)
if [ -n "$api_pids" ]; then
    echo -e "${YELLOW}  发现已运行的 API，先停止旧进程...${NC}"
    kill $api_pids 2>/dev/null || true
    sleep 1
fi

source /opt/ros/humble/setup.bash
source install/setup.bash
source .venv/bin/activate

export PYTHONPATH="${PWD}/build/lanbao_data:${PWD}/build/lanbao_interfaces:${PWD}/build/lanbao_core:${PWD}/build/lanbao_strategy:${PWD}/build/lanbao_backtest:${PWD}/build/lanbao_risk:${PWD}/build/lanbao_monitor:${PWD}/install/lanbao_interfaces/lib/python3.10/site-packages:${PWD}/install/lanbao_core/lib/python3.10/site-packages:${PWD}/install/lanbao_data/lib/python3.10/site-packages:${PWD}/install/lanbao_strategy/lib/python3.10/site-packages:${PWD}/install/lanbao_backtest/lib/python3.10/site-packages:${PWD}/install/lanbao_risk/lib/python3.10/site-packages:${PWD}/install/lanbao_monitor/lib/python3.10/site-packages:${PYTHONPATH}"
export LD_LIBRARY_PATH="${PWD}/install/lanbao_interfaces/lib:/opt/ros/humble/lib/x86_64-linux-gnu:/opt/ros/humble/lib:${LD_LIBRARY_PATH}"

nohup uvicorn lanbao_backtest.api.main:app --host 0.0.0.0 --port 8000 > logs/backtest_api.log 2>&1 &
echo $! > logs/backtest_api.pid
echo -e "${GREEN}  ✓ Backtest API 已启动 (PID: $!)${NC}"

# 3. 启动 Backtest Web（后台）
echo ""
echo -e "${BLUE}[3/3] 启动 Backtest Web (port 8502)...${NC}"

# 先停止已存在的 Web
web_pids=$(pgrep -f "vite.*port 8502" || true)
if [ -z "$web_pids" ]; then
    web_pids=$(pgrep -f "node.*vite" || true)
fi
if [ -n "$web_pids" ]; then
    echo -e "${YELLOW}  发现已运行的 Web，先停止旧进程...${NC}"
    kill $web_pids 2>/dev/null || true
    sleep 1
fi

cd src/lanbao_backtest/web
if [ ! -d "node_modules" ]; then
    echo "  首次运行，安装依赖..."
    npm install
fi

nohup npm run dev > ../../../logs/backtest_web.log 2>&1 &
echo $! > ../../../logs/backtest_web.pid
echo -e "${GREEN}  ✓ Backtest Web 已启动 (PID: $!)${NC}"

cd ../..

echo ""
echo -e "${GREEN}=======================================${NC}"
echo -e "${GREEN}  所有服务已启动                      ${NC}"
echo -e "${GREEN}=======================================${NC}"
echo ""
echo "服务状态:"
echo "  ROS2 节点:     ./scripts/start_nodes.sh 启动"
echo "  Backtest API:  http://localhost:8000"
echo "  Backtest Web:  http://localhost:8502"
echo ""
echo "查看日志:"
echo "  tail -f logs/backtest_api.log"
echo "  tail -f logs/backtest_web.log"
echo ""
echo "停止所有服务:"
echo "  ./scripts/stop_all.sh"
