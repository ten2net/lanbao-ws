"""
ROS2 客户端工具 — 供 Dashboard 等非 ROS2 常驻进程调用
通过命令行接口返回 JSON 格式的节点状态数据
"""
import json
import sys
import rclpy
from rclpy.node import Node
from lanbao_interfaces.srv import GetNodeStatus, GetDataStats, GetDataQuality, GetSyncStatus


def get_node_status(node_name: str = "") -> dict:
    """
    调用 monitor/nodes 服务获取节点状态

    Args:
        node_name: 指定节点名称，空字符串获取所有节点

    Returns:
        JSON 可序列化的字典
    """
    if not rclpy.ok():
        rclpy.init()

    node = Node("dashboard_ros2_client")
    client = node.create_client(GetNodeStatus, "monitor/nodes")

    try:
        if not client.wait_for_service(timeout_sec=3.0):
            return {"error": "monitor/nodes 服务不可用，请确保 monitor_node 已启动"}

        request = GetNodeStatus.Request()
        request.node_name = node_name

        future = client.call_async(request)
        rclpy.spin_until_future_complete(node, future, timeout_sec=3.0)

        if future.done():
            response = future.result()
            return {
                "success": response.success,
                "statuses": [
                    {
                        "node_name": s.node_name,
                        "node_type": s.node_type,
                        "status": s.status,
                        "cpu_usage": s.cpu_usage,
                        "memory_usage": s.memory_usage,
                        "message_count": s.message_count,
                        "last_error": s.last_error,
                        "timestamp": s.timestamp,
                    }
                    for s in response.statuses
                ],
            }
        else:
            return {"error": "调用 monitor/nodes 服务超时"}
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


def _call_service(service_type, service_name, build_request, extract_response, timeout_sec=5.0):
    """通用 ROS2 服务调用辅助函数"""
    if not rclpy.ok():
        rclpy.init()

    node = Node("dashboard_ros2_client")
    client = node.create_client(service_type, service_name)

    try:
        if not client.wait_for_service(timeout_sec=3.0):
            return {"error": f"{service_name} 服务不可用"}

        request = service_type.Request()
        build_request(request)

        future = client.call_async(request)
        rclpy.spin_until_future_complete(node, future, timeout_sec=timeout_sec)

        if future.done():
            response = future.result()
            return extract_response(response)
        else:
            return {"error": f"调用 {service_name} 服务超时"}
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


def get_data_stats() -> dict:
    """调用 data/stats 服务获取数据概况"""
    def extract(response):
        stats = response.stats
        return {
            "success": response.success,
            "stats": {
                "total_records": stats.total_records,
                "total_symbols": stats.total_symbols,
                "start_date": stats.start_date,
                "end_date": stats.end_date,
                "db_size_mb": stats.db_size_mb,
                "exchange_names": list(stats.exchange_names),
                "exchange_counts": list(stats.exchange_counts),
            }
        }
    return _call_service(GetDataStats, "data/stats", lambda r: None, extract)


def get_data_quality() -> dict:
    """调用 data/quality 服务获取数据质量"""
    def extract(response):
        return {
            "success": response.success,
            "items": [
                {
                    "check_name": item.check_name,
                    "pass_count": item.pass_count,
                    "fail_count": item.fail_count,
                    "status": item.status,
                    "description": item.description,
                }
                for item in response.items
            ]
        }
    return _call_service(GetDataQuality, "data/quality", lambda r: None, extract)


def get_sync_status() -> dict:
    """调用 data/sync_status 服务获取同步状态"""
    def extract(response):
        detail = response.detail
        return {
            "success": response.success,
            "detail": {
                "status": detail.status,
                "last_sync_time": detail.last_sync_time,
                "total_symbols": detail.total_symbols,
                "success_count": detail.success_count,
                "failed_count": detail.failed_count,
                "duration_seconds": detail.duration_seconds,
                "message": detail.message,
            }
        }
    return _call_service(GetSyncStatus, "data/sync_status", lambda r: None, extract)


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "nodes"
    if cmd == "nodes":
        result = get_node_status(sys.argv[2] if len(sys.argv) > 2 else "")
    elif cmd == "stats":
        result = get_data_stats()
    elif cmd == "quality":
        result = get_data_quality()
    elif cmd == "sync":
        result = get_sync_status()
    else:
        result = {"error": f"未知命令: {cmd}"}
    print(json.dumps(result, ensure_ascii=False, indent=2))
