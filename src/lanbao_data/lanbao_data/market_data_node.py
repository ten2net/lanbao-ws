"""
市场数据节点 - ROS2节点实现
"""
import os
import rclpy
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy
from loguru import logger
import pandas as pd
from datetime import datetime, timedelta
import json

from lanbao_core import DataProcessorNode, NodeConfig
from lanbao_interfaces.msg import MarketData, SystemAlert
from lanbao_interfaces.srv import GetMarketData

from .tushare_adapter import TushareAdapter
from .tdx_adapter import TDXAdapter
from .akshare_adapter import AKShareAdapter
from .miniqmt_adapter import MiniQMTAdapter
from .duckdb_storage import DuckDBStorage


class MarketDataNode(DataProcessorNode):
    """
    市场数据节点
    
    职责:
    - 从多个数据源获取实时和历史数据（Tushare, 通达信, AkShare, MiniQMT）
    - 数据质量验证
    - 数据持久化到DuckDB
    - 通过ROS2发布数据
    """
    
    def __init__(self):
        config = NodeConfig(
            node_name='market_data_node',
            node_type='market_data',
            publish_rate=1.0
        )
        super().__init__('market_data_node', config)
        
        # 数据源适配器字典
        self._adapters = {}
        self._data_sources = []  # 按优先级排序的数据源列表
        self._storage: DuckDBStorage = None
        
        # 数据缓存
        self._subscribed_symbols = set()
        self._last_data = {}
        
    def _setup_data_sources(self):
        """设置数据源"""
        # 获取数据源配置，默认为'tushare,akshare'
        data_source_config = os.getenv('LANBAO_DATA_SOURCES', 'tushare,akshare').lower()
        enabled_sources = [s.strip() for s in data_source_config.split(',')]
        
        logger.info(f"配置的数据源: {enabled_sources}")
        
        # 初始化各数据源适配器
        for source in enabled_sources:
            try:
                if source == 'tushare':
                    adapter = TushareAdapter()
                    if adapter.is_available():
                        self._adapters['tushare'] = adapter
                        logger.info("✓ Tushare数据源初始化成功")
                    else:
                        logger.warning("✗ Tushare数据源不可用")
                        
                elif source == 'tdx':
                    adapter = TDXAdapter()
                    if adapter.is_available():
                        self._adapters['tdx'] = adapter
                        logger.info("✓ 通达信数据源初始化成功")
                    else:
                        logger.warning("✗ 通达信数据源不可用")
                        
                elif source == 'akshare':
                    adapter = AKShareAdapter()
                    if adapter.is_available():
                        self._adapters['akshare'] = adapter
                        logger.info("✓ AkShare数据源初始化成功")
                    else:
                        logger.warning("✗ AkShare数据源不可用")
                        
                elif source == 'miniqmt':
                    adapter = MiniQMTAdapter()
                    if adapter.is_available():
                        self._adapters['miniqmt'] = adapter
                        logger.info("✓ MiniQMT数据源初始化成功")
                    else:
                        logger.warning("✗ MiniQMT数据源不可用")
                        
            except Exception as e:
                logger.error(f"初始化 {source} 数据源失败: {e}")
        
        # 按优先级排序数据源
        self._data_sources = sorted(
            self._adapters.values(), 
            key=lambda x: x.priority
        )
        
        if not self._data_sources:
            error_msg = "没有可用的数据源适配器"
            logger.error(error_msg)
            self._publish_alert("ERROR", error_msg)
        else:
            source_names = [type(s).__name__ for s in self._data_sources]
            logger.info(f"已启用的数据源（按优先级）: {source_names}")
    
    def initialize(self) -> bool:
        """初始化节点"""
        try:
            # 调用父类初始化
            if not super().initialize():
                return False
            
            # 初始化存储
            db_path = self._node_config.parameters.get('db_path', './data/lanbao.duckdb')
            self._storage = DuckDBStorage(db_path)
            
            # 设置ROS2服务
            self._setup_services()
            
            # 设置定时器
            self._data_timer = self.create_timer(
                60.0,  # 每分钟更新一次数据
                self._update_data,
                callback_group=self._callback_group
            )
            
            logger.info("市场数据节点初始化完成")
            return True
            
        except Exception as e:
            logger.exception(f"市场数据节点初始化失败: {e}")
            return False
    
    def _setup_services(self):
        """设置ROS2服务"""
        # 获取市场数据服务
        self._get_data_service = self.create_service(
            GetMarketData,
            'market_data/get',
            self._handle_get_market_data,
            callback_group=self._callback_group
        )
        
        logger.info("市场数据服务已设置")
    
    def _get_data_from_source(self, symbol: str, start_date: Optional[str], 
                               end_date: Optional[str]) -> pd.DataFrame:
        """
        从数据源获取数据，支持fallback机制
        
        Returns:
            DataFrame或空DataFrame
        """
        # 先从本地存储查询
        data = self._storage.get_daily_data(symbol, start_date, end_date)
        
        if not data.empty and len(data) >= 10:
            logger.debug(f"从本地缓存获取 {symbol} 数据: {len(data)} 条")
            return data
        
        # 本地数据不完整，从远程数据源获取
        for adapter in self._data_sources:
            source_name = type(adapter).__name__
            try:
                logger.info(f"尝试从 {source_name} 获取 {symbol} 数据")
                data = adapter.get_daily_data(symbol, start_date, end_date)
                
                if not data.empty:
                    # 保存到本地
                    self._storage.save_daily_data(symbol, data)
                    logger.info(f"✓ 从 {source_name} 成功获取 {len(data)} 条数据")
                    return data
                else:
                    logger.warning(f"✗ {source_name} 返回空数据")
                    
            except Exception as e:
                logger.warning(f"✗ 从 {source_name} 获取数据失败: {e}")
                continue
        
        return pd.DataFrame()
    
    def _handle_get_market_data(self, request, response):
        """
        处理获取市场数据请求
        """
        try:
            symbol = request.symbol
            start_date = request.start_date if request.start_date else None
            end_date = request.end_date if request.end_date else None
            
            logger.info(f"收到数据请求: {symbol} [{start_date} ~ {end_date}]")
            
            # 获取数据（支持多数据源fallback）
            data = self._get_data_from_source(symbol, start_date, end_date)
            
            if data.empty:
                response.success = False
                response.message = f"未找到 {symbol} 的数据"
                return response
            
            # 转换为ROS消息
            response.data = []
            for _, row in data.iterrows():
                msg = MarketData()
                msg.header.stamp = self.get_clock().now().to_msg()
                msg.symbol = symbol
                msg.open = float(row['open'])
                msg.high = float(row['high'])
                msg.low = float(row['low'])
                msg.close = float(row['close'])
                msg.volume = float(row['volume'])
                msg.amount = float(row.get('amount', 0))
                msg.data_source = row.get('data_source', 'unknown')
                msg.timestamp = int(row['date'].timestamp() * 1000) if hasattr(row['date'], 'timestamp') else 0
                response.data.append(msg)
            
            response.success = True
            response.message = f"成功获取 {len(response.data)} 条数据"
            
            logger.info(f"返回 {len(response.data)} 条数据")
            
        except Exception as e:
            logger.error(f"处理数据请求失败: {e}")
            response.success = False
            response.message = f"处理失败: {str(e)}"
        
        return response
    
    def _update_data(self):
        """定时更新数据"""
        try:
            # 获取热门股票列表并更新
            # 这里简化处理，实际可以根据配置获取
            if not self._subscribed_symbols:
                return
            
            for symbol in self._subscribed_symbols:
                # 检查是否需要更新
                self._refresh_symbol_data(symbol)
                
        except Exception as e:
            logger.error(f"更新数据失败: {e}")
    
    def _refresh_symbol_data(self, symbol: str):
        """刷新股票数据"""
        try:
            # 获取最近一个交易日的数据
            today = datetime.now().strftime('%Y%m%d')
            
            # 尝试从优先级最高的数据源获取
            for adapter in self._data_sources:
                try:
                    data = adapter.get_daily_data(symbol, today, today)
                    
                    if not data.empty:
                        self._storage.save_daily_data(symbol, data)
                        self._last_data[symbol] = data.iloc[-1].to_dict()
                        logger.debug(f"刷新 {symbol} 数据完成 ({type(adapter).__name__})")
                        return
                        
                except Exception as e:
                    logger.warning(f"从 {type(adapter).__name__} 刷新 {symbol} 数据失败: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"刷新 {symbol} 数据失败: {e}")
    
    def process_data(self, data):
        """处理数据 - 实现基类方法"""
        # 数据质量验证
        quality_report = self.validate_quality(data)
        
        if not quality_report['valid']:
            logger.warning(f"数据质量检查未通过: {quality_report['issues']}")
            return None
        
        return data
    
    def start(self) -> bool:
        """启动节点"""
        try:
            logger.info("市场数据节点启动完成")
            return True
        except Exception as e:
            logger.error(f"启动失败: {e}")
            return False
    
    def stop(self):
        """停止节点"""
        if self._storage:
            self._storage.close()
        logger.info("市场数据节点已停止")
    
    def subscribe_symbol(self, symbol: str):
        """订阅股票"""
        self._subscribed_symbols.add(symbol)
        logger.info(f"订阅股票: {symbol}")
    
    def unsubscribe_symbol(self, symbol: str):
        """取消订阅"""
        self._subscribed_symbols.discard(symbol)
        logger.info(f"取消订阅股票: {symbol}")


def main(args=None):
    """节点入口函数"""
    rclpy.init(args=args)
    
    node = MarketDataNode()
    
    try:
        node.run()
    except KeyboardInterrupt:
        logger.info("收到中断信号")
    finally:
        node.shutdown()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
