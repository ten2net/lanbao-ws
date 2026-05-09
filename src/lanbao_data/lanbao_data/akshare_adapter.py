"""
AkShare数据源适配器
使用akshare库获取A股数据
"""
import os
import time
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from loguru import logger


class AKShareAdapter:
    """
    AkShare数据适配器
    
    提供A股数据的获取接口，基于akshare库
    """
    
    def __init__(self):
        """
        初始化AkShare适配器
        """
        try:
            import akshare as ak
            self._ak = ak
        except ImportError:
            raise ImportError("akshare库未安装，请运行: pip install akshare")
        
        self._last_request_time = 0
        self._min_interval = 3.0  # 最小请求间隔(秒)，akshare对频繁请求有限制
        self._priority = 3  # 数据源优先级
        
        logger.info("AkShare适配器初始化完成")
    
    @property
    def priority(self) -> int:
        """数据源优先级"""
        return self._priority
    
    def is_available(self) -> bool:
        """检查数据源是否可用"""
        try:
            self._rate_limit()
            # 尝试获取上证指数数据来测试连接
            df = self._ak.stock_zh_index_daily(symbol="sh000001")
            return not df.empty
        except Exception as e:
            logger.error(f"AkShare连接测试失败: {e}")
            return False
    
    def _rate_limit(self):
        """速率限制"""
        elapsed = time.time() - self._last_request_time
        if elapsed < self._min_interval:
            time.sleep(self._min_interval - elapsed)
        self._last_request_time = time.time()
    
    def _convert_symbol(self, symbol: str) -> str:
        """
        转换股票代码格式为akshare格式
        
        Args:
            symbol: 原始代码，如 '000001' 或 '000001.SZ'
            
        Returns:
            akshare格式代码，如 'sz000001'
        """
        if '.' in symbol:
            code, exchange = symbol.split('.')
            exchange_map = {'SZ': 'sz', 'SH': 'sh', 'BJ': 'bj'}
            return f"{exchange_map.get(exchange, 'sz')}{code}"
        
        # 根据代码规则判断交易所
        if symbol.startswith('6') or symbol.startswith('5') or symbol.startswith('9'):
            return f"sh{symbol}"
        else:
            return f"sz{symbol}"
    
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
            
            # 转换代码格式
            ak_symbol = self._convert_symbol(symbol)
            
            # 设置默认日期
            if not end_date:
                end_date = datetime.now().strftime('%Y%m%d')
            if not start_date:
                start_date = (datetime.now() - timedelta(days=365)).strftime('%Y%m%d')
            
            # 转换日期格式为akshare需要的格式 YYYYMMDD -> YYYYMMDD
            # akshare使用stock_zh_a_hist接口
            code = symbol.split('.')[0] if '.' in symbol else symbol
            
            df = self._ak.stock_zh_a_hist(
                symbol=code,
                period="daily",
                start_date=start_date,
                end_date=end_date,
                adjust="qfq"  # 前复权
            )
            
            if df is None or df.empty:
                logger.warning(f"未获取到 {symbol} 的数据")
                return pd.DataFrame()
            
            # 标准化列名
            df = df.rename(columns={
                '日期': 'date',
                '开盘': 'open',
                '最高': 'high',
                '最低': 'low',
                '收盘': 'close',
                '成交量': 'volume',
                '成交额': 'amount',
                '振幅': 'amplitude',
                '涨跌幅': 'change_pct',
                '涨跌额': 'change',
                '换手率': 'turnover'
            })
            
            # 转换日期
            df['date'] = pd.to_datetime(df['date'])
            df = df.sort_values('date')
            
            # 添加symbol和数据源标记
            df['symbol'] = symbol
            df['data_source'] = 'akshare'
            
            logger.debug(f"获取 {symbol} 日线数据: {len(df)} 条")
            return df
            
        except Exception as e:
            logger.error(f"获取 {symbol} 日线数据失败: {e}")
            return pd.DataFrame()
    
    def get_stock_list(self, market: str = 'A') -> pd.DataFrame:
        """
        获取股票列表
        
        Args:
            market: 市场类型，'A'表示A股，'SH'上海，'SZ'深圳，'BJ'北京
            
        Returns:
            DataFrame包含股票基本信息
        """
        try:
            self._rate_limit()
            
            all_stocks = []
            
            if market in ['A', 'SH']:
                # 上海A股
                df_sh = self._ak.stock_sh_a_spot_em()
                if not df_sh.empty:
                    for _, row in df_sh.iterrows():
                        code = str(row.get('代码', ''))
                        if code:
                            all_stocks.append({
                                'symbol': f"{code}.SH",
                                'name': row.get('名称', ''),
                                'market': 'SH'
                            })
            
            if market in ['A', 'SZ']:
                # 深圳A股
                df_sz = self._ak.stock_sz_a_spot_em()
                if not df_sz.empty:
                    for _, row in df_sz.iterrows():
                        code = str(row.get('代码', ''))
                        if code:
                            all_stocks.append({
                                'symbol': f"{code}.SZ",
                                'name': row.get('名称', ''),
                                'market': 'SZ'
                            })
            
            if market in ['A', 'BJ']:
                # 北京A股
                df_bj = self._ak.stock_bj_a_spot_em()
                if not df_bj.empty:
                    for _, row in df_bj.iterrows():
                        code = str(row.get('代码', ''))
                        if code:
                            all_stocks.append({
                                'symbol': f"{code}.BJ",
                                'name': row.get('名称', ''),
                                'market': 'BJ'
                            })
            
            if not all_stocks:
                return pd.DataFrame()
            
            df = pd.DataFrame(all_stocks)
            # 去重
            df = df.drop_duplicates(subset=['symbol'])
            logger.info(f"获取股票列表: {len(df)} 只")
            return df
            
        except Exception as e:
            logger.error(f"获取股票列表失败: {e}")
            return pd.DataFrame()
    
    def get_realtime_quote(self, symbol: str) -> Dict[str, Any]:
        """
        获取实时行情
        
        Args:
            symbol: 股票代码
            
        Returns:
            实时行情数据字典
        """
        try:
            self._rate_limit()
            
            code = symbol.split('.')[0] if '.' in symbol else symbol
            
            # 获取实时行情
            df = self._ak.stock_bid_ask_em(symbol=code)
            
            if df is None or df.empty:
                return {}
            
            # 获取最新行情数据
            spot_df = self._ak.stock_zh_a_spot_em()
            spot_row = spot_df[spot_df['代码'] == code]
            
            if spot_row.empty:
                return {}
            
            row = spot_row.iloc[0]
            
            return {
                'symbol': symbol,
                'open': float(row.get('今开', 0)),
                'high': float(row.get('最高', 0)),
                'low': float(row.get('最低', 0)),
                'close': float(row.get('最新价', 0)),
                'volume': float(row.get('成交量', 0)),
                'amount': float(row.get('成交额', 0)),
                'change_pct': float(row.get('涨跌幅', 0)),
                'change': float(row.get('涨跌额', 0)),
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
            
            # 设置默认日期
            if not end_date:
                end_date = datetime.now().strftime('%Y%m%d')
            if not start_date:
                start_date = (datetime.now() - timedelta(days=365)).strftime('%Y%m%d')
            
            # 转换指数代码
            code_map = {
                '000001.SH': 'sh000001',  # 上证指数
                '399001.SZ': 'sz399001',  # 深证成指
                '399006.SZ': 'sz399006',  # 创业板指
                '000016.SH': 'sh000016',  # 上证50
                '000300.SH': 'sh000300',  # 沪深300
                '000905.SH': 'sh000905',  # 中证500
            }
            
            ak_code = code_map.get(index_code)
            if not ak_code:
                # 尝试自动转换
                if '.SH' in index_code:
                    ak_code = f"sh{index_code.split('.')[0]}"
                elif '.SZ' in index_code:
                    ak_code = f"sz{index_code.split('.')[0]}"
                else:
                    ak_code = index_code
            
            df = self._ak.stock_zh_index_daily(symbol=ak_code)
            
            if df is None or df.empty:
                return pd.DataFrame()
            
            # 筛选日期范围
            df['date'] = pd.to_datetime(df['date'])
            start_dt = datetime.strptime(start_date, '%Y%m%d')
            end_dt = datetime.strptime(end_date, '%Y%m%d')
            
            df = df[(df['date'] >= start_dt) & (df['date'] <= end_dt)]
            df = df.sort_values('date')
            
            # 添加数据源标记
            df['data_source'] = 'akshare'
            
            return df
            
        except Exception as e:
            logger.error(f"获取指数 {index_code} 数据失败: {e}")
            return pd.DataFrame()
    
    def get_stock_news(self, symbol: str) -> pd.DataFrame:
        """
        获取个股新闻（AkShare特有功能）
        
        Args:
            symbol: 股票代码
            
        Returns:
            DataFrame包含新闻数据
        """
        try:
            self._rate_limit()
            
            code = symbol.split('.')[0] if '.' in symbol else symbol
            df = self._ak.stock_news_em(symbol=code)
            
            if df is None or df.empty:
                return pd.DataFrame()
            
            df['data_source'] = 'akshare'
            return df
            
        except Exception as e:
            logger.error(f"获取 {symbol} 新闻失败: {e}")
            return pd.DataFrame()
