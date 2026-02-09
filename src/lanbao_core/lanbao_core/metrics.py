"""
揽宝系统指标收集模块
"""
import time
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass, field
from collections import deque
import threading


@dataclass
class MetricPoint:
    """指标数据点"""
    timestamp: float
    value: float
    labels: Dict[str, str] = field(default_factory=dict)


class MetricsCollector:
    """指标收集器"""
    
    def __init__(self, node_name: str, max_history: int = 1000):
        self.node_name = node_name
        self.max_history = max_history
        self._metrics: Dict[str, deque] = {}
        self._counters: Dict[str, float] = {}
        self._gauges: Dict[str, float] = {}
        self._lock = threading.Lock()
        
    def record(self, metric_name: str, value: float, labels: Optional[Dict[str, str]] = None):
        """记录指标值"""
        with self._lock:
            if metric_name not in self._metrics:
                self._metrics[metric_name] = deque(maxlen=self.max_history)
            
            point = MetricPoint(
                timestamp=time.time(),
                value=value,
                labels=labels or {}
            )
            self._metrics[metric_name].append(point)
    
    def increment_counter(self, counter_name: str, value: float = 1.0):
        """增加计数器"""
        with self._lock:
            self._counters[counter_name] = self._counters.get(counter_name, 0) + value
    
    def set_gauge(self, gauge_name: str, value: float):
        """设置仪表盘值"""
        with self._lock:
            self._gauges[gauge_name] = value
    
    def get_counter(self, counter_name: str) -> float:
        """获取计数器值"""
        with self._lock:
            return self._counters.get(counter_name, 0)
    
    def get_gauge(self, gauge_name: str) -> float:
        """获取仪表盘值"""
        with self._lock:
            return self._gauges.get(gauge_name, 0)
    
    def get_metric_history(self, metric_name: str, limit: int = 100) -> List[MetricPoint]:
        """获取指标历史"""
        with self._lock:
            history = self._metrics.get(metric_name, deque())
            return list(history)[-limit:]
    
    def get_latest(self, metric_name: str) -> Optional[MetricPoint]:
        """获取最新指标值"""
        with self._lock:
            history = self._metrics.get(metric_name, deque())
            return history[-1] if history else None
    
    def get_average(self, metric_name: str, window: int = 100) -> float:
        """获取移动平均值"""
        with self._lock:
            history = self._metrics.get(metric_name, deque())
            if not history:
                return 0.0
            values = [p.value for p in list(history)[-window:]]
            return sum(values) / len(values) if values else 0.0
    
    def get_all_metrics(self) -> Dict[str, List[Dict]]:
        """获取所有指标"""
        with self._lock:
            result = {}
            for name, history in self._metrics.items():
                result[name] = [
                    {
                        'timestamp': p.timestamp,
                        'value': p.value,
                        'labels': p.labels
                    }
                    for p in history
                ]
            return result
    
    def get_summary(self) -> Dict:
        """获取指标摘要"""
        with self._lock:
            return {
                'node_name': self.node_name,
                'counters': self._counters.copy(),
                'gauges': self._gauges.copy(),
                'metric_names': list(self._metrics.keys()),
            }
    
    def clear(self):
        """清空所有指标"""
        with self._lock:
            self._metrics.clear()
            self._counters.clear()
            self._gauges.clear()


class PerformanceTimer:
    """性能计时器 - 上下文管理器"""
    
    def __init__(self, collector: MetricsCollector, metric_name: str, 
                 labels: Optional[Dict[str, str]] = None):
        self.collector = collector
        self.metric_name = metric_name
        self.labels = labels or {}
        self.start_time: Optional[float] = None
        self.duration: Optional[float] = None
        
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.duration = time.time() - self.start_time
        self.collector.record(self.metric_name, self.duration, self.labels)
        return False  # 不处理异常
