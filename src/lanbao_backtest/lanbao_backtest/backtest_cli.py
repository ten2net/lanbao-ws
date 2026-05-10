"""
回测 CLI 工具 — 供 Dashboard 等非 ROS2 常驻进程调用回测服务
通过命令行参数触发 ROS2 回测服务调用，输出 JSON 结果
"""
import json
import sys
import rclpy
from rclpy.node import Node
from lanbao_interfaces.srv import RunBacktest


def run_backtest(strategy_id: str, symbol: str, start_date: str, end_date: str) -> dict:
    """调用 backtest/run 服务执行回测

    Args:
        strategy_id: 策略ID，如 ma_cross, rsi
        symbol: 股票代码，如 000001.SZ
        start_date: 开始日期 (YYYYMMDD)
        end_date: 结束日期 (YYYYMMDD)

    Returns:
        JSON 可序列化的字典
    """
    if not rclpy.ok():
        rclpy.init()

    node = Node("backtest_cli_client")
    client = node.create_client(RunBacktest, "backtest/run")

    try:
        if not client.wait_for_service(timeout_sec=5.0):
            return {"success": False, "message": "backtest/run 服务不可用，请确保 backtest_engine_node 已启动"}

        request = RunBacktest.Request()
        request.strategy_id = strategy_id
        request.symbol = symbol
        request.start_date = start_date
        request.end_date = end_date

        future = client.call_async(request)
        rclpy.spin_until_future_complete(node, future, timeout_sec=120.0)

        if future.done():
            response = future.result()
            return {
                "success": response.success,
                "backtest_id": response.backtest_id,
                "message": response.message,
            }
        else:
            return {"success": False, "message": "回测服务调用超时（超过120秒）"}
    except Exception as e:
        return {"success": False, "message": f"回测调用异常: {str(e)}"}
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    if len(sys.argv) < 5:
        print(json.dumps(
            {"success": False, "message": "用法: python backtest_cli.py <strategy_id> <symbol> <start_date> <end_date>"},
            ensure_ascii=False
        ))
        sys.exit(1)

    result = run_backtest(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4])
    print(json.dumps(result, ensure_ascii=False))
