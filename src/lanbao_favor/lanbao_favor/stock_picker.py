"""选股引擎 - 封装 stock-select 客户端"""
import os
import time
from typing import List, Dict, Optional, Set
from dataclasses import dataclass

from loguru import logger

from .models import FavorCondition


@dataclass
class StockInfo:
    code: str
    name: str
    market_type: str = ""
    source_condition: str = ""


class StockPicker:
    """选股器 - 支持板块热度过滤和市值二次过滤"""

    def __init__(self):
        self._selector = None
        self._hot_sector_codes: Optional[Set[str]] = None

        try:
            from stock_select.client import StockSelector
            self._selector = StockSelector()
        except ImportError:
            logger.warning("stock-select 工具未安装，选股功能不可用")

    def pick(self, condition: FavorCondition) -> List[StockInfo]:
        start = time.time()
        logger.info(f"开始选股: {condition.name} -> {condition.query}")

        if self._selector is None:
            logger.warning("stock-select 不可用，跳过选股")
            return []

        try:
            result = self._selector.select(condition.query, max_results=condition.max_results)
            stocks = [
                StockInfo(
                    code=s.code,
                    name=s.name,
                    market_type=getattr(s, 'market_type', ''),
                    source_condition=condition.name,
                )
                for s in result.stocks
            ]
            logger.info(f"  stock-select 返回 {len(stocks)} 只")

            if condition.filter_min_cap_yi:
                stocks = self._filter_by_market_cap(stocks, condition.filter_min_cap_yi)

            if condition.filter_hot_sector:
                stocks = self._filter_by_hot_sectors(stocks)

            duration = int((time.time() - start) * 1000)
            logger.info(f"  选股完成: {len(stocks)} 只, 耗时 {duration}ms")
            return stocks

        except Exception as e:
            logger.error(f"  选股失败: {e}")
            return []

    def pick_multiple(self, conditions: List[FavorCondition]) -> Dict[str, List[StockInfo]]:
        results = {}
        for condition in conditions:
            results[condition.name] = self.pick(condition)
        return results

    def _filter_by_market_cap(self, stocks: List[StockInfo], min_cap_yi: float) -> List[StockInfo]:
        try:
            from eastmoney_mcp.api import EastMoneyAPI

            appkey = os.getenv('EASTMONEY_APPKEY')
            cookie = os.getenv('EASTMONEY_COOKIE')
            if not appkey or not cookie:
                logger.warning("EastMoney 凭证未配置，跳过市值过滤")
                return stocks

            api = EastMoneyAPI(appkey=appkey, cookie=cookie)
            codes = [s.code for s in stocks]
            quotes = api.get_batch_quotes(codes)
            quote_dict = {q.code: q for q in quotes}

            filtered = []
            for stock in stocks:
                quote = quote_dict.get(stock.code)
                if quote and hasattr(quote, 'circulating_cap') and quote.circulating_cap:
                    if quote.circulating_cap >= min_cap_yi:
                        filtered.append(stock)
                    else:
                        logger.debug(f"  过滤 {stock.code}: 流通市值{quote.circulating_cap:.1f}亿 < {min_cap_yi}亿")
                else:
                    filtered.append(stock)

            logger.info(f"  市值过滤: {len(stocks)} -> {len(filtered)} 只")
            return filtered

        except Exception as e:
            logger.warning(f"市值过滤失败: {e}，跳过过滤")
            return stocks

    def _filter_by_hot_sectors(self, stocks: List[StockInfo]) -> List[StockInfo]:
        try:
            from strategies.sector_rotation import SectorRotationTracker

            tracker = SectorRotationTracker()
            top_sectors = tracker.get_top_sectors(n=3, validate=True, max_validate=10)

            hot_codes = set()
            for sector in top_sectors.top_sectors:
                if not sector.is_valid:
                    continue
                codes = tracker.get_sector_stocks(sector.name)
                if codes:
                    hot_codes.update(codes)

            if not hot_codes:
                logger.warning("无法获取热门板块，跳过板块过滤")
                return stocks

            filtered = [s for s in stocks if s.code in hot_codes]
            if not filtered:
                logger.warning(f"板块过滤后为空，回退到全市场（原{len(stocks)}只）")
                return stocks

            logger.info(f"  板块过滤: {len(stocks)} -> {len(filtered)} 只")
            return filtered

        except Exception as e:
            logger.warning(f"板块过滤失败: {e}，跳过过滤")
            return stocks
