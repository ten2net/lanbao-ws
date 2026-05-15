"""ROS2 数据服务客户端

封装对所有数据节点的 ROS2 Service 调用。
ai_research_node 使用此客户端获取数据，不直接访问 DuckDB/数据源。
"""
import asyncio
from typing import Optional, Dict, Any, List

import pandas as pd
from loguru import logger

from lanbao_interfaces.srv import GetMarketData, GetFinancialData, SaveResearchReport, GetResearchReport


class ROS2DataClient:
    """ROS2 数据服务客户端"""

    def __init__(self, node):
        """
        Args:
            node: ROS2 Node 实例，用于创建 Service Client
        """
        self._node = node
        self._clients = {}
        self._init_clients()

    def _init_clients(self):
        """初始化所有 Service Client"""
        self._clients['market_data'] = self._node.create_client(
            GetMarketData, '/market_data/get'
        )
        self._clients['financial'] = self._node.create_client(
            GetFinancialData, '/data_sync/financial'
        )
        self._clients['save_report'] = self._node.create_client(
            SaveResearchReport, '/data_sync/save_research_report'
        )
        self._clients['get_report'] = self._node.create_client(
            GetResearchReport, '/data_sync/get_research_report'
        )
        logger.info("ROS2 Data Client 初始化完成")

    async def _call_service(self, client_name: str, request, timeout: float = 30.0):
        """异步调用 ROS2 Service"""
        client = self._clients.get(client_name)
        if not client:
            raise RuntimeError(f"未知的 service client: {client_name}")

        # 等待服务可用
        if not client.wait_for_service(timeout_sec=5.0):
            raise TimeoutError(f"Service {client_name} 不可用")

        future = client.call_async(request)

        # 手动轮询等待 future 完成（asyncio.wrap_future 不支持 rclpy.task.Future）
        import time
        start = time.time()
        while not future.done():
            if time.time() - start > timeout:
                raise TimeoutError(f"Service {client_name} 调用超时 ({timeout}s)")
            await asyncio.sleep(0.05)

        return future.result()

    async def get_ohlcv(self, symbol: str, start_date: str, end_date: str,
                        freq: str = "daily") -> Optional[pd.DataFrame]:
        """获取历史行情数据"""
        request = GetMarketData.Request()
        request.symbol = symbol
        request.start_date = start_date
        request.end_date = end_date
        request.freq = freq

        response = await self._call_service('market_data', request)

        if not response.success or not response.data:
            logger.warning(f"获取行情数据失败: {response.message}")
            return None

        # 转换 MarketData[] 为 DataFrame
        data = []
        for item in response.data:
            data.append({
                'timestamp': item.timestamp,
                'open': item.open,
                'high': item.high,
                'low': item.low,
                'close': item.close,
                'volume': item.volume,
            })

        df = pd.DataFrame(data)
        df['date'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('date', inplace=True)
        return df.sort_index()

    async def get_financial_data(self, symbol: str,
                                 report_type: str = "indicator") -> Optional[Dict]:
        """获取财务数据"""
        request = GetFinancialData.Request()
        request.symbol = symbol
        request.report_type = report_type

        response = await self._call_service('financial', request)

        if not response.success:
            logger.warning(f"获取财务数据失败: {response.message}")
            return None

        import json
        try:
            return json.loads(response.data_json) if response.data_json else None
        except json.JSONDecodeError:
            logger.error("财务数据 JSON 解析失败")
            return None

    async def save_report_metadata(self, report_id: str, report_type: str,
                                   symbols: List[str], summary: str, verdict: str,
                                   confidence: float, report_json: str) -> bool:
        """保存报告元数据到 DuckDB（通过 data_sync_node）"""
        request = SaveResearchReport.Request()
        request.report_id = report_id
        request.report_type = report_type
        request.symbols = symbols
        request.summary = summary
        request.verdict = verdict
        request.confidence = confidence
        request.report_json = report_json

        response = await self._call_service('save_report', request)
        return response.success

    async def get_report_metadata(self, report_id: str) -> Optional[Dict]:
        """获取报告元数据"""
        request = GetResearchReport.Request()
        request.report_id = report_id

        response = await self._call_service('get_report', request)

        if not response.found:
            return None

        return {
            "report_id": report_id,
            "report_json": response.report_json,
            "created_at": response.created_at,
        }
