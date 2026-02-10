"""
通达信数据源适配器
使用pytdx库连接通达信行情服务器
"""
import os
import time
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from loguru import logger


class TDXAdapter:
    """
    通达信数据适配器
    
    提供A股数据的获取接口，支持连接通达信行情服务器
    """
    
    def __init__(self, api_host: Optional[str] = None, api_port: Optional[int] = None):
        """
        初始化通达信适配器
        
        Args:
            api_host: 通达信服务器地址，如果不提供则使用默认服务器
            api_port: 通达信服务器端口，如果不提供则使用默认端口
        """
        try:
            from pytdx.hq import TdxHq_API
            self._api = TdxHq_API()
        except ImportError:
            raise ImportError("pytdx库未安装，请运行: pip install pytdx")
        
        # 默认通达信行情服务器列表
        self._hosts = [
            ('119.147.212.81', 7709),  # 深圳主站1
            ('218.75.126.150', 7709),  # 深圳主站2
            ('115.238.56.198', 7709),  # 上海主站1
            ('124.160.88.183', 7709),  # 上海主站2
        ]
        
        if api_host and api_port:
            self._hosts.insert(0, (api_host, api_port))
        
        self._connection = None
        self._last_request_time = 0
        self._min_interval = 0.05  # 最小请求间隔(秒)
        self._priority = 2  # 数据源优先级
        
        logger.info("通达信适配器初始化完成")
    
    @property
    def priority(self) -> int:
        """数据源优先级"""
        return self._priority
    
    def _connect(self) -> bool:
        """连接到通达信服务器"""
        if self._connection:
            return True
        
        for host, port in self._hosts:
            try:
                self._connection = self._api.connect(host, port)
                if self._connection:
                    logger.info(f"通达信连接成功: {host}:{port}")
                    return True
            except Exception as e:
                logger.debug(f"连接 {host}:{port} 失败: {e}")
                continue
        
        logger.error("通达信所有服务器连接失败")
        return False
    
    def _disconnect(self):
        """断开连接"""
        if self._connection:
            try:
                self._api.disconnect()
            except:
                pass
            self._connection = None
    
    def is_available(self) -> bool:
        """检查数据源是否可用"""
        try:
            return self._connect()
        except Exception as e:
            logger.error(f"通达信连接测试失败: {e}")
            return False
    
    def _rate_limit(self):
        """速率限制"""
        elapsed = time.time() - self._last_request_time
        if elapsed < self._min_interval:
            time.sleep(self._min_interval - elapsed)
        self._last_request_time = time.time()
    
    def _get_market_code(self, symbol: str) -> int:
        """
        获取市场代码
        
        Args:
            symbol: 股票代码
            
        Returns:
            0=深圳, 1=上海
        """
        code = symbol.split('.')[0] if '.' in symbol else symbol
        if code.startswith('6') or code.startswith('5') or code.startswith('9'):
            return 1  # 上海
        return 0  # 深圳
    
    def _convert_symbol(self, symbol: str) -> str:
        """
        转换股票代码格式
        
        Args:
            symbol: 原始代码，如 '000001' 或 '000001.SZ'
            
        Returns:
            纯数字代码
        """
        if '.' in symbol:
            return symbol.split('.')[0]
        return symbol
    
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
            if not self._connect():
                return pd.DataFrame()
            
            self._rate_limit()
            
            # 转换代码格式
            code = self._convert_symbol(symbol)
            market = self._get_market_code(symbol)
            
            # 设置默认日期
            if not end_date:
                end_date = datetime.now().strftime('%Y%m%d')
            if not start_date:
                start_date = (datetime.now() - timedelta(days=365)).strftime('%Y%m%d')
            
            start_dt = datetime.strptime(start_date, '%Y%m%d')
            end_dt = datetime.strptime(end_date, '%Y%m%d')
            
            # 计算需要获取的数据条数（通达信一次最多获取800条）
            days_needed = (end_dt - start_dt).days + 1
            
            all_data = []
            
            # 通达信获取数据是从最新日期往前获取
            # 我们需要分批获取，直到覆盖start_date
            offset = 0
            max_retries = 10
            retry_count = 0
            
            while retry_count < max_retries:
                self._rate_limit()
                
                try:
                    data = self._api.get_security_bars(
                        category=9,  # 日线
                        market=market,
                        code=code,
                        start=offset,
                        count=800
                    )
                except Exception as e:
                    logger.warning(f"获取数据失败，尝试重连: {e}")
                    self._disconnect()
                    if not self._connect():
                        break
                    continue
                
                if not data:
                    break
                
                for item in data:
                    trade_date = datetime(
                        item['year'], item['month'], item['day']
                    )
                    
                    # 检查是否在日期范围内
                    if trade_date < start_dt:
                        retry_count = max_retries
                        break
                    if trade_date > end_dt:
                        continue
                    
                    all_data.append({
                        'date': trade_date,
                        'open': item['open'],
                        'high': item['high'],
                        'low': item['low'],
                        'close': item['close'],
                        'volume': item['vol'],
                        'amount': item['amount']
                    })
                
                offset += 800
                retry_count += 1
                
                # 如果获取的数据不足800条，说明已经到最早的数据了
                if len(data) < 800:
                    break
            
            if not all_data:
                logger.warning(f"未获取到 {symbol} 的数据")
                return pd.DataFrame()
            
            df = pd.DataFrame(all_data)
            df = df.sort_values('date')
            df['symbol'] = symbol
            df['data_source'] = 'tdx'
            
            logger.debug(f"获取 {symbol} 日线数据: {len(df)} 条")
            return df
            
        except Exception as e:
            logger.error(f"获取 {symbol} 日线数据失败: {e}")
            return pd.DataFrame()
    
    def get_stock_list(self, market: str = 'A') -> pd.DataFrame:
        """
        获取股票列表
        
        Args:
            market: 市场类型，'A'表示A股，'SH'上海，'SZ'深圳
            
        Returns:
            DataFrame包含股票基本信息
        """
        try:
            if not self._connect():
                return pd.DataFrame()
            
            all_stocks = []
            
            # 深圳市场 (market=0)
            if market in ['A', 'SZ']:
                self._rate_limit()
                stocks = self._api.get_security_list(0, 0)
                if stocks:
                    for stock in stocks:
                        all_stocks.append({
                            'symbol': f"{stock['code']}.SZ",
                            'name': stock['name'],
                            'market': 'SZ'
                        })
            
            # 上海市场 (market=1)
            if market in ['A', 'SH']:
                self._rate_limit()
                stocks = self._api.get_security_list(1, 0)
                if stocks:
                    for stock in stocks:
                        all_stocks.append({
                            'symbol': f"{stock['code']}.SH",
                            'name': stock['name'],
                            'market': 'SH'
                        })
            
            if not all_stocks:
                return pd.DataFrame()
            
            df = pd.DataFrame(all_stocks)
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
            if not self._connect():
                return {}
            
            self._rate_limit()
            
            code = self._convert_symbol(symbol)
            market = self._get_market_code(symbol)
            
            # 获取5档行情
            data = self._api.get_security_quotes([(market, code)])
            
            if not data:
                return {}
            
            quote = data[0]
            return {
                'symbol': symbol,
                'open': quote['open'],
                'high': quote['high'],
                'low': quote['low'],
                'close': quote['price'],  # 当前价格
                'volume': quote['vol'],
                'amount': quote['amount'],
                'bid1': quote.get('bid1', 0),
                'ask1': quote.get('ask1', 0),
                'bid_vol1': quote.get('bid_vol1', 0),
                'ask_vol1': quote.get('ask_vol1', 0),
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
        # 通达信指数代码格式略有不同
        # 直接使用get_daily_data获取
        return self.get_daily_data(index_code, start_date, end_date)
