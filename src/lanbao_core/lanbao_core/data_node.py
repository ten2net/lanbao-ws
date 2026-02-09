"""
揽宝数据处理节点基类
"""
from abc import abstractmethod
from typing import List, Optional, Dict, Any
import pandas as pd
from loguru import logger

from .base_node import LanBaoBaseNode
from lanbao_interfaces.msg import MarketData


class DataProcessorNode(LanBaoBaseNode):
    """
    数据处理节点基类
    
    负责:
    - 多源数据采集
    - 数据质量验证
    - 数据融合
    """
    
    def __init__(self, node_name: str, config=None):
        super().__init__(node_name, config)
        self._node_config.node_type = "data_processor"
        self._data_sources: List[Any] = []
        self._data_buffer: Dict[str, pd.DataFrame] = {}
        self._buffer_size = 1000
        
    def initialize(self) -> bool:
        """初始化数据节点"""
        try:
            # 初始化数据源
            self._setup_data_sources()
            
            # 注册健康检查
            self._health.register_check(
                'data_source_health',
                self._check_data_sources,
                interval_seconds=30
            )
            
            logger.info(f"[{self.get_name()}] 数据节点初始化完成")
            return True
            
        except Exception as e:
            logger.error(f"[{self.get_name()}] 数据节点初始化失败: {e}")
            return False
    
    @abstractmethod
    def _setup_data_sources(self):
        """
        设置数据源
        子类必须实现此方法
        """
        pass
    
    @abstractmethod
    def process_data(self, data: Any) -> Any:
        """
        处理数据
        子类必须实现此方法
        
        Args:
            data: 输入数据
            
        Returns:
            处理后的数据
        """
        pass
    
    def validate_quality(self, data: pd.DataFrame) -> Dict[str, Any]:
        """
        验证数据质量
        
        Args:
            data: 待验证的数据
            
        Returns:
            质量报告
        """
        report = {
            'valid': True,
            'issues': [],
            'score': 100.0
        }
        
        # 检查空值
        null_count = data.isnull().sum().sum()
        if null_count > 0:
            report['issues'].append(f"发现 {null_count} 个空值")
            report['score'] -= min(20, null_count * 2)
        
        # 检查价格异常
        if 'close' in data.columns:
            zero_prices = (data['close'] == 0).sum()
            if zero_prices > 0:
                report['issues'].append(f"发现 {zero_prices} 个零价格")
                report['score'] -= min(30, zero_prices * 5)
            
            negative_prices = (data['close'] < 0).sum()
            if negative_prices > 0:
                report['issues'].append(f"发现 {negative_prices} 个负价格")
                report['score'] -= 50
        
        # 检查时间连续性
        if 'timestamp' in data.columns or 'trade_date' in data.columns:
            time_col = 'timestamp' if 'timestamp' in data.columns else 'trade_date'
            # 简单的连续性检查
            if len(data) > 1:
                # 这里可以添加更复杂的检查
                pass
        
        report['score'] = max(0, report['score'])
        report['valid'] = report['score'] >= 60
        
        return report
    
    def _check_data_sources(self) -> Dict:
        """检查数据源健康状态"""
        healthy_count = sum(1 for ds in self._data_sources if getattr(ds, 'is_available', lambda: False)())
        total_count = len(self._data_sources)
        
        if healthy_count == total_count:
            return {
                'status': HealthStatus.HEALTHY,
                'message': f'所有 {total_count} 个数据源正常',
                'metadata': {'healthy': healthy_count, 'total': total_count}
            }
        elif healthy_count > 0:
            return {
                'status': HealthStatus.DEGRADED,
                'message': f'{healthy_count}/{total_count} 个数据源正常',
                'metadata': {'healthy': healthy_count, 'total': total_count}
            }
        else:
            return {
                'status': HealthStatus.UNHEALTHY,
                'message': '所有数据源不可用',
                'metadata': {'healthy': 0, 'total': total_count}
            }
    
    def get_best_data_source(self) -> Optional[Any]:
        """
        获取最佳数据源
        
        Returns:
            优先级最高的可用数据源
        """
        available = [ds for ds in self._data_sources 
                     if getattr(ds, 'is_available', lambda: False)()]
        if not available:
            return None
        
        # 按优先级排序
        available.sort(key=lambda ds: getattr(ds, 'priority', 999))
        return available[0]
    
    def buffer_data(self, symbol: str, data: pd.DataFrame):
        """
        缓存数据
        
        Args:
            symbol: 股票代码
            data: 数据DataFrame
        """
        if symbol not in self._data_buffer:
            self._data_buffer[symbol] = data
        else:
            self._data_buffer[symbol] = pd.concat([
                self._data_buffer[symbol],
                data
            ]).drop_duplicates().tail(self._buffer_size)
    
    def get_buffered_data(self, symbol: str) -> Optional[pd.DataFrame]:
        """
        获取缓存的数据
        
        Args:
            symbol: 股票代码
            
        Returns:
            缓存的数据
        """
        return self._data_buffer.get(symbol)


# 导入HealthStatus用于类型检查
from .health_monitor import HealthStatus
