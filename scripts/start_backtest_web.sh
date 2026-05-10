#!/bin/bash
# scripts/start_backtest_web.sh
# 启动回测面板前端开发服务器

set -e

cd "$(dirname "$0")/.."

echo "启动回测面板前端 (port 8502)..."
cd src/lanbao_backtest/web

if [ ! -d "node_modules" ]; then
    echo "首次运行，安装依赖..."
    npm install
fi

npm run dev
