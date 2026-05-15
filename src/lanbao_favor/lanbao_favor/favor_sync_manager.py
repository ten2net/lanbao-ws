"""EastMoney 自选股同步管理器"""
import os
import sys
from typing import List, Dict
from loguru import logger

sys.path.insert(0, '/root/lanbao/tools/eastmoney-mcp-server/src')
from eastmoney_mcp.api import EastMoneyAPI


class FavorSyncManager:
    """管理 EastMoney 自选股的同步操作"""

    def __init__(self, appkey: str = None, cookie: str = None):
        self._appkey = appkey or os.getenv('EASTMONEY_APPKEY')
        self._cookie = cookie or os.getenv('EASTMONEY_COOKIE')

        if not self._appkey or not self._cookie:
            raise ValueError("EastMoney 凭证未配置")

        self._api = EastMoneyAPI(appkey=self._appkey, cookie=self._cookie)

    def get_watchlist(self, group_name: str = "自选股") -> List[Dict]:
        try:
            stocks = self._api.get_watchlist(group_name=group_name)
            return [{'code': s.code, 'name': s.name} for s in stocks]
        except Exception as e:
            logger.error(f"获取自选股失败: {e}")
            return []

    def add_stocks(self, codes: List[str], group_name: str = "自选股") -> bool:
        if not codes:
            return True
        try:
            return self._api.add_to_watchlist(codes, group_name=group_name)
        except Exception as e:
            logger.error(f"添加自选股失败: {e}")
            return False

    def remove_stocks(self, codes: List[str], group_name: str = "自选股") -> bool:
        if not codes:
            return True
        try:
            return self._api.remove_from_watchlist(codes, group_name=group_name)
        except Exception as e:
            logger.error(f"移除自选股失败: {e}")
            return False

    def create_group(self, group_name: str) -> bool:
        try:
            return self._api.create_group(group_name)
        except Exception as e:
            logger.error(f"创建分组失败: {e}")
            return False

    def get_groups(self) -> List[Dict]:
        try:
            groups = self._api.get_watchlist_groups()
            return [{'id': g.id, 'name': g.name} for g in groups]
        except Exception as e:
            logger.error(f"获取分组失败: {e}")
            return []
