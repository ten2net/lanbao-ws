#!/bin/bash
# 揽宝系统全量停止脚本（节点 + API + Web）

echo "正在停止揽宝系统所有服务..."

# 1. 停止 ROS2 节点
./scripts/stop_nodes.sh

# 2. 停止 Backtest API
api_pid_file="logs/backtest_api.pid"
if [ -f "$api_pid_file" ]; then
    api_pid=$(cat "$api_pid_file" 2>/dev/null)
    if [ -n "$api_pid" ] && kill -0 "$api_pid" 2>/dev/null; then
        echo "停止 backtest_api (PID: $api_pid)..."
        kill "$api_pid" 2>/dev/null
        sleep 1
        if kill -0 "$api_pid" 2>/dev/null; then
            kill -9 "$api_pid" 2>/dev/null
        fi
    fi
    rm -f "$api_pid_file"
fi

# 兜底：通过进程名停止 API
api_pids=$(pgrep -f "uvicorn lanbao_backtest\.api\.main:app" || true)
if [ -n "$api_pids" ]; then
    echo "停止 backtest_api (PID: $api_pids)..."
    kill -9 $api_pids 2>/dev/null || true
fi

# 3. 停止 Backtest Web
web_pid_file="logs/backtest_web.pid"
if [ -f "$web_pid_file" ]; then
    web_pid=$(cat "$web_pid_file" 2>/dev/null)
    if [ -n "$web_pid" ] && kill -0 "$web_pid" 2>/dev/null; then
        echo "停止 backtest_web (PID: $web_pid)..."
        kill "$web_pid" 2>/dev/null
        sleep 1
        if kill -0 "$web_pid" 2>/dev/null; then
            kill -9 "$web_pid" 2>/dev/null
        fi
    fi
    rm -f "$web_pid_file"
fi

# 兜底：通过进程名停止 Web
web_pids=$(pgrep -f "vite.*port 8502" || true)
if [ -z "$web_pids" ]; then
    web_pids=$(pgrep -f "node.*vite" || true)
fi
if [ -n "$web_pids" ]; then
    echo "停止 backtest_web (PID: $web_pids)..."
    kill -9 $web_pids 2>/dev/null || true
fi

# 清理 esbuild 子进程
esbuild_pids=$(pgrep -f "esbuild.*ping" || true)
if [ -n "$esbuild_pids" ]; then
    kill -9 $esbuild_pids 2>/dev/null || true
fi

echo "所有服务已停止"
