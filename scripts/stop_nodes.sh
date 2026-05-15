#!/bin/bash
# 揽宝系统节点停止脚本

echo "正在停止揽宝系统节点..."

# 节点列表（与 start_nodes.sh 对应）
NODES=(
    "rosbridge_server"
    "market_data"
    "data_sync"
    "backtest"
    "strategy"
    "risk"
    "monitor"
    "system_metrics"
    "favor"
)

# 额外服务（非 ROS2 节点但属于系统）
EXTRA_SERVICES=(
    "backtest_api"
    "backtest_web"
)

# 停止 rosbridge 相关进程（launch + websocket 子进程）
_stop_rosbridge() {
    local pids=""
    local launch_pid=$(pgrep -f "rosbridge_websocket_launch")
    local ws_pid=$(pgrep -f "/rosbridge_websocket ")

    # 1. 停止 launch 进程：先 SIGINT，等待后 SIGKILL
    if [ -n "$launch_pid" ]; then
        echo "停止 rosbridge_server launch (PID: $launch_pid)..."
        kill -INT "$launch_pid" 2>/dev/null
        sleep 2
        if kill -0 "$launch_pid" 2>/dev/null; then
            kill -9 "$launch_pid" 2>/dev/null
        fi
    fi

    # 2. 清理残留的 websocket 子进程（防止变成孤儿进程）
    if [ -n "$ws_pid" ]; then
        echo "停止 rosbridge_websocket (PID: $ws_pid)..."
        kill -9 "$ws_pid" 2>/dev/null
    fi
}

# 停止函数
stop_node_by_name() {
    local node_name=$1
    local pids

    # rosbridge 使用专门的停止逻辑
    if [ "$node_name" = "rosbridge_server" ]; then
        _stop_rosbridge
        return 0
    fi

    # 根据节点名匹配 Python 模块路径
    case "$node_name" in
        "market_data")
            pids=$(pgrep -f "lanbao_data\.market_data_node")
            ;;
        "data_sync")
            pids=$(pgrep -f "lanbao_data\.data_sync_node")
            ;;
        "backtest")
            pids=$(pgrep -f "lanbao_backtest\.backtest_engine_node")
            ;;
        "strategy")
            pids=$(pgrep -f "lanbao_strategy\.strategy_manager_node")
            ;;
        "risk")
            pids=$(pgrep -f "lanbao_risk\.risk_control_node")
            ;;
        "monitor")
            pids=$(pgrep -f "lanbao_monitor\.monitor_node")
            ;;
        "system_metrics")
            pids=$(pgrep -f "lanbao_monitor\.system_metrics_node")
            ;;
        "favor")
            pids=$(pgrep -f "lanbao_favor\.favor_node")
            ;;
        "backtest_api")
            pids=$(pgrep -f "uvicorn lanbao_backtest\.api\.main:app")
            ;;
        "backtest_web")
            pids=$(pgrep -f "vite.*port 8502")
            if [ -z "$pids" ]; then
                pids=$(pgrep -f "node.*vite")
            fi
            # 同时停止 esbuild 子进程
            child_pids=$(pgrep -f "esbuild.*ping")
            if [ -n "$child_pids" ]; then
                pids="$pids $child_pids"
            fi
            ;;
        *)
            pids=""
            ;;
    esac

    if [ -n "$pids" ]; then
        echo "停止 $node_name (PID: $pids)..."
        for pid in $pids; do
            kill "$pid" 2>/dev/null
        done
        return 0
    fi
    return 1
}

stopped_count=0

for node_name in "${NODES[@]}"; do
    pid_file="logs/${node_name}.pid"
    stopped=false

    # 1. 优先通过 pid 文件精确停止
    if [ -f "$pid_file" ]; then
        pid=$(cat "$pid_file" 2>/dev/null)
        if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
            if [ "$node_name" = "rosbridge_server" ]; then
                _stop_rosbridge
            else
                echo "停止 $node_name (PID: $pid)..."
                kill "$pid" 2>/dev/null
            fi
            stopped=true
            stopped_count=$((stopped_count + 1))
        fi
        rm -f "$pid_file"
    fi

    # 2. pid 文件不存在或进程已失效时，通过进程名查找
    if [ "$stopped" = false ]; then
        if stop_node_by_name "$node_name"; then
            stopped_count=$((stopped_count + 1))
        fi
    fi
done

# 3. 停止额外服务（backtest API / web）
for service_name in "${EXTRA_SERVICES[@]}"; do
    if stop_node_by_name "$service_name"; then
        stopped_count=$((stopped_count + 1))
    fi
done

# 4. 清理可能残留的 launcher 脚本
rm -f logs/*_launcher.sh

echo "已停止 $stopped_count 个进程"
