#!/bin/bash
# 揽宝系统节点停止脚本

echo "正在停止揽宝系统节点..."

# 停止所有节点
for pid_file in logs/*.pid; do
    if [ -f "$pid_file" ]; then
        node_name=$(basename "$pid_file" .pid)
        pid=$(cat "$pid_file")
        
        if kill -0 "$pid" 2>/dev/null; then
            echo "停止 $node_name (PID: $pid)..."
            kill "$pid"
            rm "$pid_file"
        else
            echo "$node_name 已不在运行"
            rm "$pid_file"
        fi
    fi
done

echo "所有节点已停止"
