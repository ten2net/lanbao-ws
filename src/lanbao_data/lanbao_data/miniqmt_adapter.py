"""
MiniQMT数据源适配器
使用迅投QMT的Python API获取A股数据
"""
import os
import time
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from loguru import logger


class MiniQMTAdapter:
    """
    MiniQMT数据适配器
    
    提供A股数据的获取接口，基于迅投QMT的Python API
    需要安装QMT客户端并配置miniQMT模式
    """
    
    def __init__(self, qmt_path: Optional[str] = None, account_id: Optional[str] = None):
        """
        初始化MiniQMT适配器
        
        Args:
            qmt_path: QMT安装路径，如果不提供则从环境变量获取
            account_id: 资金账号，如果不提供则从环境变量获取
        """
        self._qmt_path = qmt_path or os.getenv('QMT_PATH')
        self._account_id = account_id or os.getenv('QMT_ACCOUNT_ID')
        
        self._xtdata = None
        self._xttype = None
        self._connected = False
        self._priority = 1  # 数据源优先级（实盘交易优先）
        
        # 尝试导入xtquant模块
        try:
            # 如果QMT路径已设置，添加到Python路径
            if self._qmt_path and os.path.exists(self._qmt_path):
                import sys
                sys.path.insert(0, self._qmt_path)
            
            from xtquant import xtdata
            from xtquant import xttype
            self._xtdata = xtdata
            self._xttype = xttype
            logger.info("MiniQMT适配器初始化完成")
        except ImportError:
            logger.warning("xtquant库未找到，MiniQMT适配器将以模拟模式运行")
            logger.warning("如需实盘连接，请安装QMT并配置QMT_PATH环境变量")
    
    @property
    def priority(self) -> int:
        """数据源优先级"""
        return self._priority
    
    def is_available(self) -> bool:
        """检查数据源是否可用"""
        if self._xtdata is None:
            logger.warning("MiniQMT未初始化，请先安装QMT")
            return False
        
        try:
            # 尝试获取市场状态来测试连接
            self._xtdata.get_trading_status()
            return True
        except Exception as e:
            logger.error(f"MiniQMT连接测试失败: {e}")
            return False
    
    def _convert_symbol(self, symbol: str) -> str:
        """
        转换股票代码格式为QMT格式
        
        Args:
            symbol: 原始代码，如 '000001' 或 '000001.SZ'
            
        Returns:
            QMT格式代码，如 '000001.SZ'
        """
        if '.' in symbol:
            return symbol
        
        # 根据代码规则判断交易所
        if symbol.startswith('6') or symbol.startswith('5') or symbol.startswith('9'):
            return f"{symbol}.SH"
        elif symbol.startswith('4') or symbol.startswith('8'):
            return f"{symbol}.BJ"
        else:
            return f"{symbol}.SZ"
    
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
        if self._xtdata is None:
            logger.warning("MiniQMT未初始化")
            return pd.DataFrame()
        
        try:
            # 转换代码格式
            qmt_symbol = self._convert_symbol(symbol)
            
            # 设置默认日期
            if not end_date:
                end_date = datetime.now().strftime('%Y%m%d')
            if not start_date:
                start_date = (datetime.now() - timedelta(days=365)).strftime('%Y%m%d')
            
            # 下载历史数据
            self._xtdata.download_history_data(
                stock_code=qmt_symbol,
                period='1d',
                start_time=start_date,
                end_time=end_date
            )
            
            # 获取本地历史数据
            data = self._xtdata.get_local_data(
                field_list=['time', 'open', 'high', 'low', 'close', 'volume', 'amount'],
                stock_list=[qmt_symbol],
                period='1d',
                start_time=start_date,
                end_time=end_date
            )
            
            if not data or qmt_symbol not in data:
                logger.warning(f"未获取到 {symbol} 的数据")
                return pd.DataFrame()
            
            df = data[qmt_symbol]
            
            if df is None or df.empty:
                return pd.DataFrame()
            
            # 转换时间戳
            if 'time' in df.columns:
                df['date'] = pd.to_datetime(df['time'], unit='ms')
            
            # 标准化列名
            column_map = {
                'open': 'open',
                'high': 'high',
                'low': 'low',
                'close': 'close',
                'volume': 'volume',
                'amount': 'amount'
            }
            
            df = df.rename(columns=column_map)
            
            # 添加symbol和数据源标记
            df['symbol'] = symbol
            df['data_source'] = 'miniqmt'
            
            df = df.sort_values('date')
            
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
        if self._xtdata is None:
            logger.warning("MiniQMT未初始化")
            return pd.DataFrame()
        
        try:
            all_stocks = []
            
            # 获取深圳市场股票
            if market in ['A', 'SZ']:
                sz_stocks = self._xtdata.get_stock_list_in_sector('深圳A股')
                for stock in sz_stocks:
                    all_stocks.append({
                        'symbol': stock,
                        'market': 'SZ'
                    })
            
            # 获取上海市场股票
            if market in ['A', 'SH']:
                sh_stocks = self._xtdata.get_stock_list_in_sector('上海A股')
                for stock in sh_stocks:
                    all_stocks.append({
                        'symbol': stock,
                        'market': 'SH'
                    })
            
            # 获取北京市场股票
            if market in ['A', 'BJ']:
                bj_stocks = self._xtdata.get_stock_list_in_sector('北京A股')
                for stock in bj_stocks:
                    all_stocks.append({
                        'symbol': stock,
                        'market': 'BJ'
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
        if self._xtdata is None:
            logger.warning("MiniQMT未初始化")
            return {}
        
        try:
            qmt_symbol = self._convert_symbol(symbol)
            
            # 订阅实时行情
            self._xtdata.subscribe_quote(qmt_symbol, period='tick')
            
            # 获取最新tick数据
            tick_data = self._xtdata.get_full_tick([qmt_symbol])
            
            if not tick_data or qmt_symbol not in tick_data:
                return {}
            
            tick = tick_data[qmt_symbol]
            
            return {
                'symbol': symbol,
                'open': tick.get('open', 0),
                'high': tick.get('high', 0),
                'low': tick.get('low', 0),
                'close': tick.get('lastPrice', 0),
                'volume': tick.get('volume', 0),
                'amount': tick.get('amount', 0),
                'bid1': tick.get('bid1', 0),
                'ask1': tick.get('ask1', 0),
                'bid_vol1': tick.get('bid_vol1', 0),
                'ask_vol1': tick.get('ask_vol1', 0),
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
        # 指数数据获取方式与个股相同
        return self.get_daily_data(index_code, start_date, end_date)
    
    def get_tick_data(self, symbol: str, trade_date: str) -> pd.DataFrame:
        """
        获取tick数据（MiniQMT特有功能）
        
        Args:
            symbol: 股票代码
            trade_date: 交易日期 'YYYYMMDD'
            
        Returns:
            DataFrame包含tick数据
        """
        if self._xtdata is None:
            logger.warning("MiniQMT未初始化")
            return pd.DataFrame()
        
        try:
            qmt_symbol = self._convert_symbol(symbol)
            
            # 下载tick数据
            self._xtdata.download_history_data(
                stock_code=qmt_symbol,
                period='tick',
                start_time=trade_date,
                end_time=trade_date
            )
            
            # 获取本地tick数据
            data = self._xtdata.get_local_data(
                field_list=[],
                stock_list=[qmt_symbol],
                period='tick',
                start_time=trade_date,
                end_time=trade_date
            )
            
            if not data or qmt_symbol not in data:
                return pd.DataFrame()
            
            df = data[qmt_symbol]
            
            if df is None or df.empty:
                return pd.DataFrame()
            
            df['symbol'] = symbol
            df['data_source'] = 'miniqmt'
            
            return df
            
        except Exception as e:
            logger.error(f"获取 {symbol} tick数据失败: {e}")
            return pd.DataFrame()
    
    def subscribe_realtime(self, symbols: List[str], callback=None):
        """
        订阅实时行情（MiniQMT特有功能）
        
        Args:
            symbols: 股票代码列表
            callback: 回调函数，接收行情数据
        """
        if self._xtdata is None:
            logger.warning("MiniQMT未初始化")
            return
        
        try:
            qmt_symbols = [self._convert_symbol(s) for s in symbols]
            
            for symbol in qmt_symbols:
                self._xtdata.subscribe_quote(symbol, period='tick')
            
            if callback:
                self._xtdata.run(callback)
            
            logger.info(f"已订阅 {len(symbols)} 只股票的实时行情")
            
        except Exception as e:
            logger.error(f"订阅实时行情失败: {e}")
