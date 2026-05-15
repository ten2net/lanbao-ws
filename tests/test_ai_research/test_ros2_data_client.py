"""Test ROS2DataClient — 数据转换逻辑"""
import asyncio
from datetime import datetime, timezone

import pandas as pd
import pytest

from lanbao_ai_research.data_client.ros2_data_client import ROS2DataClient
from lanbao_interfaces.msg import MarketData


class MockFuture:
    """模拟已完成的 rclpy 异步 future"""

    def __init__(self, result):
        self._result = result
        self._done = True

    def done(self):
        return self._done

    def result(self):
        return self._result


class MockServiceClient:
    """模拟 ROS2 ServiceClient"""

    def __init__(self, response):
        self._response = response

    def wait_for_service(self, timeout_sec=None):
        return True

    def call_async(self, request):
        return MockFuture(self._response)


class MockNode:
    """模拟 ROS2 Node，只提供 create_client"""

    def __init__(self, response_map):
        self._response_map = response_map

    def create_client(self, srv_type, name):
        return MockServiceClient(self._response_map.get(name))


def make_market_data_response(timestamps_ms, prices):
    """构造 GetMarketData 响应（timestamp 为毫秒级 Unix epoch）"""
    from lanbao_interfaces.srv import GetMarketData

    response = GetMarketData.Response()
    response.success = True
    response.message = "ok"
    for ts, price in zip(timestamps_ms, prices):
        msg = MarketData()
        msg.timestamp = ts
        msg.open = price
        msg.high = price + 1.0
        msg.low = price - 1.0
        msg.close = price
        msg.volume = 1000.0
        response.data.append(msg)
    return response


@pytest.mark.asyncio
async def test_get_ohlcv_parses_millisecond_timestamp():
    """
    MarketData.timestamp 由 market_data_node 以毫秒写入：
        int(row['date'].timestamp() * 1000)
    ros2_data_client 必须按 unit='ms' 解析，否则会得到超限或错误的日期。
    """
    # 2024-01-02 00:00:00 UTC = 1704153600000 ms
    # 2024-01-03 00:00:00 UTC = 1704239999000 ms（接近边界，容易暴露秒/毫秒混淆）
    ts_ms = [1704153600000, 1704240000000]
    expected_dates = [
        datetime(2024, 1, 2),
        datetime(2024, 1, 3),
    ]
    prices = [100.0, 101.0]

    response = make_market_data_response(ts_ms, prices)
    node = MockNode({"/market_data/get": response})
    client = ROS2DataClient(node)

    df = await client.get_ohlcv("600519", "20240101", "20240103")

    assert df is not None
    assert len(df) == 2
    pd.testing.assert_index_equal(
        df.index, pd.DatetimeIndex(expected_dates, name="date")
    )
    assert df.iloc[0]["close"] == 100.0
    assert df.iloc[1]["close"] == 101.0
