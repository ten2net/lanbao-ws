#!/bin/bash
# scripts/start_backtest_api.sh
# 启动回测面板 FastAPI 后端

set -e

cd "$(dirname "$0")/.."

echo "启动回测面板 API..."
source /opt/ros/humble/setup.bash
source install/setup.bash
source .venv/bin/activate

# 设置环境变量
export PYTHONPATH="${PWD}/src:${PWD}/install/lanbao_interfaces/lib/python3.10/site-packages:${PWD}/install/lanbao_core/lib/python3.10/site-packages:${PWD}/build/lanbao_interfaces:${PWD}/build/lanbao_core:${PYTHONPATH}"
export LD_LIBRARY_PATH="${PWD}/install/lanbao_interfaces/lib:/opt/ros/humble/lib/x86_64-linux-gnu:/opt/ros/humble/lib:${LD_LIBRARY_PATH}"

uvicorn lanbao_backtest.api.main:app --host 0.0.0.0 --port 8000 --reload
