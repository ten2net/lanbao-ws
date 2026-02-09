"""
揽宝系统健康监控模块
"""
import time
import threading
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum


class HealthStatus(Enum):
    """健康状态枚举"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class HealthCheck:
    """健康检查项"""
    name: str
    status: HealthStatus
    message: str
    last_check: float
    response_time_ms: float
    metadata: Dict = field(default_factory=dict)


class HealthMonitor:
    """健康监控器"""
    
    def __init__(self, node_name: str):
        self.node_name = node_name
        self._checks: Dict[str, HealthCheck] = {}
        self._check_functions: Dict[str, Callable] = {}
        self._lock = threading.Lock()
        self._running = False
        self._monitor_thread: Optional[threading.Thread] = None
        
    def register_check(self, name: str, check_func: Callable, 
                       interval_seconds: int = 60):
        """注册健康检查函数"""
        with self._lock:
            self._check_functions[name] = {
                'func': check_func,
                'interval': interval_seconds,
                'last_run': 0
            }
            self._checks[name] = HealthCheck(
                name=name,
                status=HealthStatus.UNKNOWN,
                message="未检查",
                last_check=0,
                response_time_ms=0
            )
    
    def start_monitoring(self):
        """开始监控"""
        self._running = True
        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()
    
    def stop_monitoring(self):
        """停止监控"""
        self._running = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=5)
    
    def _monitor_loop(self):
        """监控循环"""
        while self._running:
            current_time = time.time()
            
            with self._lock:
                checks = list(self._check_functions.items())
            
            for name, check_info in checks:
                if current_time - check_info['last_run'] >= check_info['interval']:
                    self._run_check(name, check_info)
            
            time.sleep(1)  # 每秒检查一次
    
    def _run_check(self, name: str, check_info: Dict):
        """运行单个检查"""
        start_time = time.time()
        try:
            result = check_info['func']()
            response_time = (time.time() - start_time) * 1000
            
            with self._lock:
                self._checks[name] = HealthCheck(
                    name=name,
                    status=result.get('status', HealthStatus.HEALTHY),
                    message=result.get('message', '正常'),
                    last_check=time.time(),
                    response_time_ms=response_time,
                    metadata=result.get('metadata', {})
                )
                check_info['last_run'] = time.time()
                
        except Exception as e:
            with self._lock:
                self._checks[name] = HealthCheck(
                    name=name,
                    status=HealthStatus.UNHEALTHY,
                    message=f"检查异常: {str(e)}",
                    last_check=time.time(),
                    response_time_ms=(time.time() - start_time) * 1000
                )
    
    def check_health(self, check_name: Optional[str] = None) -> Dict:
        """检查健康状态"""
        with self._lock:
            if check_name:
                check = self._checks.get(check_name)
                if check:
                    return {
                        'name': check.name,
                        'status': check.status.value,
                        'message': check.message,
                        'last_check': check.last_check,
                        'response_time_ms': check.response_time_ms
                    }
                return {'error': f'检查项不存在: {check_name}'}
            
            # 返回所有检查
            overall_status = HealthStatus.HEALTHY
            checks_list = []
            
            for check in self._checks.values():
                checks_list.append({
                    'name': check.name,
                    'status': check.status.value,
                    'message': check.message,
                    'last_check': check.last_check,
                    'response_time_ms': check.response_time_ms
                })
                
                if check.status == HealthStatus.UNHEALTHY:
                    overall_status = HealthStatus.UNHEALTHY
                elif check.status == HealthStatus.DEGRADED and overall_status != HealthStatus.UNHEALTHY:
                    overall_status = HealthStatus.DEGRADED
            
            return {
                'node_name': self.node_name,
                'overall_status': overall_status.value,
                'timestamp': time.time(),
                'checks': checks_list
            }
    
    def is_healthy(self) -> bool:
        """检查是否健康"""
        health = self.check_health()
        return health.get('overall_status') == HealthStatus.HEALTHY.value
    
    def get_overall_status(self) -> HealthStatus:
        """获取整体健康状态"""
        health = self.check_health()
        status_str = health.get('overall_status', 'unknown')
        return HealthStatus(status_str)
