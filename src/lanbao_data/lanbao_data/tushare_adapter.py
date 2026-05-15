"""
Tushare数据源适配器
"""

import os
import time
import pandas as pd
import tushare as ts
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from loguru import logger


class TushareAdapter:
    """
    Tushare数据适配器

    提供A股数据的获取接口
    """

    def __init__(self, api_token: Optional[str] = None):
        """
        初始化Tushare适配器

        Args:
            api_token: Tushare API Token，如果不提供则从环境变量获取
        """
        self._token = api_token or os.getenv("TUSHARE_TOKEN")
        if not self._token:
            raise ValueError("Tushare API Token未提供，请设置TUSHARE_TOKEN环境变量")

        self._pro = ts.pro_api(self._token)
        self._last_request_time = 0
        self._min_interval = 0.1  # 最小请求间隔(秒)
        self._financial_interval = 0.75  # 80 req/min ≈ 0.75s per request
        self._last_financial_request = 0
        self._priority = 1  # 数据源优先级

        logger.info("Tushare适配器初始化完成")

    @property
    def priority(self) -> int:
        """数据源优先级"""
        return self._priority

    def is_available(self) -> bool:
        """检查数据源是否可用"""
        try:
            # 尝试获取股票列表来测试连接
            self._rate_limit()
            self._pro.stock_basic(limit=1)
            return True
        except Exception as e:
            logger.error(f"Tushare连接测试失败: {e}")
            return False

    def _rate_limit(self, financial=False):
        """速率限制"""
        interval = self._financial_interval if financial else self._min_interval
        last = self._last_financial_request if financial else self._last_request_time
        elapsed = time.time() - last
        if elapsed < interval:
            time.sleep(interval - elapsed)
        if financial:
            self._last_financial_request = time.time()
        else:
            self._last_request_time = time.time()

    def get_daily_data(
        self,
        symbol: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        adjust: str = "qfq",
    ) -> pd.DataFrame:
        """
        获取日线数据，支持前复权

        Args:
            symbol: 股票代码，如 '000001.SZ'
            start_date: 开始日期 'YYYYMMDD'
            end_date: 结束日期 'YYYYMMDD'
            adjust: 复权类型，'qfq'前复权(默认)，'none'不复权

        Returns:
            DataFrame包含OHLCV数据及前复权价格
        """
        try:
            self._rate_limit()

            # 转换股票代码格式
            ts_code = self._convert_symbol(symbol)

            # 设置默认日期
            if not end_date:
                end_date = datetime.now().strftime("%Y%m%d")
            if not start_date:
                start_date = (datetime.now() - timedelta(days=365)).strftime("%Y%m%d")

            df = self._pro.daily(ts_code=ts_code, start_date=start_date, end_date=end_date)

            if df is None or df.empty:
                logger.warning(f"未获取到 {symbol} 的数据")
                return pd.DataFrame()

            # 标准化列名
            df = df.rename(
                columns={
                    "ts_code": "symbol",
                    "trade_date": "date",
                    "open": "open",
                    "high": "high",
                    "low": "low",
                    "close": "close",
                    "vol": "volume",
                    "amount": "amount",
                }
            )

            # 转换日期
            df["date"] = pd.to_datetime(df["date"])
            df = df.sort_values("date")

            # 添加数据源标记
            df["data_source"] = "tushare"

            # 计算前复权价格
            if adjust == "qfq":
                adj_df = self._get_adj_factor(ts_code, start_date, end_date)
                if not adj_df.empty:
                    df = df.merge(adj_df, on=["symbol", "date"], how="left")
                    latest_adj = adj_df["adj_factor"].iloc[-1]
                    for col in ["open", "high", "low", "close"]:
                        df[f"{col}_adj"] = df[col] * df["adj_factor"] / latest_adj
                else:
                    logger.warning(f"{symbol}: 未获取到复权因子，使用原始价格")
                    for col in ["open", "high", "low", "close"]:
                        df[f"{col}_adj"] = df[col]
                    df["adj_factor"] = 1.0
            else:
                for col in ["open", "high", "low", "close"]:
                    df[f"{col}_adj"] = df[col]
                df["adj_factor"] = 1.0

            logger.debug(f"获取 {symbol} 日线数据: {len(df)} 条 ({adjust})")
            return df

        except Exception as e:
            logger.error(f"获取 {symbol} 日线数据失败: {e}")
            return pd.DataFrame()

    def _get_adj_factor(self, ts_code: str, start_date: str, end_date: str) -> pd.DataFrame:
        """
        获取复权因子（内部方法）

        Args:
            ts_code: Tushare格式代码
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            DataFrame包含symbol, date, adj_factor
        """
        try:
            self._rate_limit()

            df = self._pro.adj_factor(ts_code=ts_code, start_date=start_date, end_date=end_date)

            if df is None or df.empty:
                return pd.DataFrame()

            df = df.rename(columns={"ts_code": "symbol", "trade_date": "date"})
            df["date"] = pd.to_datetime(df["date"])
            df["adj_factor"] = df["adj_factor"].astype(float)

            return df[["symbol", "date", "adj_factor"]].sort_values("date")

        except Exception as e:
            logger.warning(f"获取 {ts_code} 复权因子失败: {e}")
            return pd.DataFrame()

    def get_trade_calendar(
        self, start_date: str, end_date: str, exchange: str = "SSE"
    ) -> List[str]:
        """
        获取交易日历

        Args:
            start_date: 开始日期 'YYYYMMDD'
            end_date: 结束日期 'YYYYMMDD'
            exchange: 交易所，默认'SSE'（上交所）

        Returns:
            交易日列表 ['YYYYMMDD', ...]
        """
        try:
            self._rate_limit()

            df = self._pro.trade_cal(exchange=exchange, start_date=start_date, end_date=end_date)

            if df is None or df.empty:
                logger.warning(f"未获取到交易日历: {start_date} ~ {end_date}")
                return []

            # 筛选开盘日
            trade_dates = df[df["is_open"] == 1]["cal_date"].tolist()
            logger.debug(f"获取交易日历: {len(trade_dates)} 个交易日")
            return trade_dates

        except Exception as e:
            logger.error(f"获取交易日历失败: {e}")
            return []

    def get_stock_list(self, market: str = "A") -> pd.DataFrame:
        """
        获取股票列表

        Args:
            market: 市场类型，'A'表示A股

        Returns:
            DataFrame包含股票基本信息
        """
        try:
            self._rate_limit()

            exchange_map = {"A": None, "SH": "SSE", "SZ": "SZSE"}  # 全部A股

            exchange = exchange_map.get(market)

            if exchange:
                df = self._pro.stock_basic(exchange=exchange)
            else:
                df = self._pro.stock_basic()

            if df is None or df.empty:
                return pd.DataFrame()

            # 标准化：ts_code -> symbol，如果已有symbol列则先删除
            if "symbol" in df.columns:
                df = df.drop(columns=["symbol"])
            df = df.rename(columns={"ts_code": "symbol"})
            df["market"] = market

            logger.info(f"获取股票列表: {len(df)} 只")
            return df

        except Exception as e:
            logger.error(f"获取股票列表失败: {e}")
            return pd.DataFrame()

    def get_realtime_quote(self, symbol: str) -> Dict[str, Any]:
        """
        获取实时行情 (使用Tushare的通用行情接口)

        Args:
            symbol: 股票代码

        Returns:
            实时行情数据字典
        """
        try:
            self._rate_limit()
            ts_code = self._convert_symbol(symbol)

            # 获取最新日线数据作为近似实时数据
            today = datetime.now().strftime("%Y%m%d")
            df = self._pro.daily(ts_code=ts_code, start_date=today, end_date=today)

            if df is None or df.empty:
                return {}

            row = df.iloc[0]
            return {
                "symbol": symbol,
                "open": float(row["open"]),
                "high": float(row["high"]),
                "low": float(row["low"]),
                "close": float(row["close"]),
                "volume": float(row["vol"]),
                "amount": float(row["amount"]),
                "timestamp": int(time.time()),
            }

        except Exception as e:
            logger.error(f"获取 {symbol} 实时行情失败: {e}")
            return {}

    def get_index_data(
        self,
        index_code: str = "000001.SH",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> pd.DataFrame:
        """
        获取指数数据

        Args:
            index_code: 指数代码
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            DataFrame包含指数数据
        """
        try:
            self._rate_limit()

            if not end_date:
                end_date = datetime.now().strftime("%Y%m%d")
            if not start_date:
                start_date = (datetime.now() - timedelta(days=365)).strftime("%Y%m%d")

            df = self._pro.index_daily(ts_code=index_code, start_date=start_date, end_date=end_date)

            if df is None or df.empty:
                return pd.DataFrame()

            df["trade_date"] = pd.to_datetime(df["trade_date"])
            df = df.sort_values("trade_date")

            return df

        except Exception as e:
            logger.error(f"获取指数 {index_code} 数据失败: {e}")
            return pd.DataFrame()

    def _get_financial_statement(
        self, symbol: str, period: str, api_method: str, statement_name: str
    ) -> pd.DataFrame:
        """
        通用财务报表获取

        Args:
            symbol: 股票代码
            period: 报告期
            api_method: Tushare API 方法名 ('balancesheet', 'income', 'cashflow')
            statement_name: 报表名称（用于日志）

        Returns:
            DataFrame
        """
        try:
            self._rate_limit(financial=True)
            ts_code = self._convert_symbol(symbol)

            df = getattr(self._pro, api_method)(ts_code=ts_code, period=period)

            if df is None or df.empty:
                logger.warning(f"未获取到 {symbol} 的{statement_name}: {period}")
                return pd.DataFrame()

            logger.debug(f"获取 {symbol} {statement_name}: {period}, {len(df)} 条")
            return df

        except Exception as e:
            logger.error(f"获取 {symbol} {statement_name}失败 ({period}): {e}")
            return pd.DataFrame()

    def get_balance_sheet(self, symbol: str, period: str) -> pd.DataFrame:
        """获取资产负债表"""
        return self._get_financial_statement(symbol, period, "balancesheet", "资产负债表")

    def get_income_statement(self, symbol: str, period: str) -> pd.DataFrame:
        """获取利润表"""
        return self._get_financial_statement(symbol, period, "income", "利润表")

    def get_cashflow_statement(self, symbol: str, period: str) -> pd.DataFrame:
        """获取现金流量表"""
        return self._get_financial_statement(symbol, period, "cashflow", "现金流量表")

    def _convert_symbol(self, symbol: str) -> str:
        """
        转换股票代码格式

        Args:
            symbol: 原始代码，如 '000001' 或 '000001.SZ'

        Returns:
            Tushare格式代码，如 '000001.SZ'
        """
        if "." in symbol:
            return symbol

        # 根据代码规则判断交易所
        if symbol.startswith("6"):
            return f"{symbol}.SH"
        else:
            return f"{symbol}.SZ"
