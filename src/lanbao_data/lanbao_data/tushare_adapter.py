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
        self._token = api_token or os.getenv('TUSHARE_TOKEN')
        if not self._token:
            raise ValueError("Tushare API Token未提供，请设置TUSHARE_TOKEN环境变量")
        
        self._pro = ts.pro_api(self._token)
        self._last_request_time = 0
        self._min_interval = 0.1  # 最小请求间隔(秒)
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
    
    def _rate_limit(self):
        """速率限制"""
        elapsed = time.time() - self._last_request_time
        if elapsed < self._min_interval:
            time.sleep(self._min_interval - elapsed)
        self._last_request_time = time.time()
    
    def get_daily_data(self, symbol: str, start_date: Optional[str] = None,
                       end_date: Optional[str] = None) -> pd.DataFrame:
        """
        获取日线数据
        
        Args:
            symbol: 股票代码，如 '000001.SZ'
            start_date: 开始日期 'YYYYMMDD'
            end_date: 结束日期 'YYYYMMDD'
            
        Returns:
            DataFrame包含OHLCV数据
        """
        try:
            self._rate_limit()
            
            # 转换股票代码格式
            ts_code = self._convert_symbol(symbol)
            
            # 设置默认日期
            if not end_date:
                end_date = datetime.now().strftime('%Y%m%d')
            if not start_date:
                start_date = (datetime.now() - timedelta(days=365)).strftime('%Y%m%d')
            
            df = self._pro.daily(
                ts_code=ts_code,
                start_date=start_date,
                end_date=end_date
            )
            
            if df is None or df.empty:
                logger.warning(f"未获取到 {symbol} 的数据")
                return pd.DataFrame()
            
            # 标准化列名
            df = df.rename(columns={
                'ts_code': 'symbol',
                'trade_date': 'date',
                'open': 'open',
                'high': 'high',
                'low': 'low',
                'close': 'close',
                'vol': 'volume',
                'amount': 'amount'
            })
            
            # 转换日期
            df['date'] = pd.to_datetime(df['date'])
            df = df.sort_values('date')
            
            # 添加数据源标记
            df['data_source'] = 'tushare'
            
            logger.debug(f"获取 {symbol} 日线数据: {len(df)} 条")
            return df
            
        except Exception as e:
            logger.error(f"获取 {symbol} 日线数据失败: {e}")
            return pd.DataFrame()
    
    def get_stock_list(self, market: str = 'A') -> pd.DataFrame:
        """
        获取股票列表
        
        Args:
            market: 市场类型，'A'表示A股
            
        Returns:
            DataFrame包含股票基本信息
        """
        try:
            self._rate_limit()
            
            exchange_map = {
                'A': None,  # 全部A股
                'SH': 'SSE',
                'SZ': 'SZSE'
            }
            
            exchange = exchange_map.get(market)
            
            if exchange:
                df = self._pro.stock_basic(exchange=exchange)
            else:
                df = self._pro.stock_basic()
            
            if df is None or df.empty:
                return pd.DataFrame()
            
            # 标准化
            df = df.rename(columns={'ts_code': 'symbol'})
            df['market'] = market
            
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
            today = datetime.now().strftime('%Y%m%d')
            df = self._pro.daily(ts_code=ts_code, start_date=today, end_date=today)
            
            if df is None or df.empty:
                return {}
            
            row = df.iloc[0]
            return {
                'symbol': symbol,
                'open': float(row['open']),
                'high': float(row['high']),
                'low': float(row['low']),
                'close': float(row['close']),
                'volume': float(row['vol']),
                'amount': float(row['amount']),
                'timestamp': int(time.time())
            }
            
        except Exception as e:
            logger.error(f"获取 {symbol} 实时行情失败: {e}")
            return {}
    
    def get_index_data(self, index_code: str = '000001.SH',
                       start_date: Optional[str] = None,
                       end_date: Optional[str] = None) -> pd.DataFrame:
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
                end_date = datetime.now().strftime('%Y%m%d')
            if not start_date:
                start_date = (datetime.now() - timedelta(days=365)).strftime('%Y%m%d')
            
            df = self._pro.index_daily(
                ts_code=index_code,
                start_date=start_date,
                end_date=end_date
            )
            
            if df is None or df.empty:
                return pd.DataFrame()
            
            df['trade_date'] = pd.to_datetime(df['trade_date'])
            df = df.sort_values('trade_date')
            
            return df
            
        except Exception as e:
            logger.error(f"获取指数 {index_code} 数据失败: {e}")
            return pd.DataFrame()
    
    def _convert_symbol(self, symbol: str) -> str:
        """
        转换股票代码格式
        
        Args:
            symbol: 原始代码，如 '000001' 或 '000001.SZ'
            
        Returns:
            Tushare格式代码，如 '000001.SZ'
        """
        if '.' in symbol:
            return symbol
        
        # 根据代码规则判断交易所
        if symbol.startswith('6'):
            return f"{symbol}.SH"
        else:
            return f"{symbol}.SZ"
