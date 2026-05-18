#!/bin/bash
# scripts/start_backtest_api.sh
# 启动回测面板 FastAPI 后端

set -e

cd "$(dirname "$0")/.."

echo "启动回测面板 API..."
source /opt/ros/humble/setup.bash
source install/setup.bash
source .venv/bin/activate

# 清除 Python 缓存，确保源码修改生效
echo "清除 Python 缓存..."
find "${PWD}/build" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find "${PWD}/src" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true

# 设置环境变量（build 目录优先，确保加载最新代码）
export PYTHONPATH="${PWD}/build/lanbao_data:${PWD}/build/lanbao_interfaces:${PWD}/build/lanbao_core:${PWD}/build/lanbao_strategy:${PWD}/build/lanbao_backtest:${PWD}/build/lanbao_risk:${PWD}/build/lanbao_monitor:${PWD}/install/lanbao_interfaces/lib/python3.10/site-packages:${PWD}/install/lanbao_core/lib/python3.10/site-packages:${PWD}/install/lanbao_data/lib/python3.10/site-packages:${PWD}/install/lanbao_strategy/lib/python3.10/site-packages:${PWD}/install/lanbao_backtest/lib/python3.10/site-packages:${PWD}/install/lanbao_risk/lib/python3.10/site-packages:${PWD}/install/lanbao_monitor/lib/python3.10/site-packages:${PYTHONPATH}"
export LD_LIBRARY_PATH="${PWD}/install/lanbao_interfaces/lib:/opt/ros/humble/lib/x86_64-linux-gnu:/opt/ros/humble/lib:${LD_LIBRARY_PATH}"

uvicorn lanbao_backtest.api.main:app --host 0.0.0.0 --port 8000 --reload
