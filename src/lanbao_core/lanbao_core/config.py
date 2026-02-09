"""
揽宝系统配置管理模块
"""
import os
import yaml
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from pathlib import Path


@dataclass
class NodeConfig:
    """节点配置类"""
    node_name: str = "default_node"
    node_type: str = "generic"
    log_level: str = "INFO"
    qos_profile: str = "default"
    
    # 通信配置
    publish_rate: float = 1.0  # 发布频率(Hz)
    timeout_ms: int = 5000     # 超时时间(ms)
    retry_count: int = 3       # 重试次数
    
    # 性能配置
    max_queue_size: int = 1000
    worker_threads: int = 4
    
    # 自定义参数
    parameters: Dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def from_yaml(cls, yaml_path: str) -> 'NodeConfig':
        """从YAML文件加载配置"""
        with open(yaml_path, 'r', encoding='utf-8') as f:
            config_dict = yaml.safe_load(f)
        return cls(**config_dict)
    
    @classmethod
    def from_env(cls) -> 'NodeConfig':
        """从环境变量加载配置"""
        return cls(
            node_name=os.getenv('LANBAO_NODE_NAME', 'default_node'),
            node_type=os.getenv('LANBAO_NODE_TYPE', 'generic'),
            log_level=os.getenv('LANBAO_LOG_LEVEL', 'INFO'),
            qos_profile=os.getenv('LANBAO_QOS_PROFILE', 'default'),
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'node_name': self.node_name,
            'node_type': self.node_type,
            'log_level': self.log_level,
            'qos_profile': self.qos_profile,
            'publish_rate': self.publish_rate,
            'timeout_ms': self.timeout_ms,
            'retry_count': self.retry_count,
            'max_queue_size': self.max_queue_size,
            'worker_threads': self.worker_threads,
            'parameters': self.parameters,
        }


@dataclass
class DataSourceConfig:
    """数据源配置"""
    name: str
    source_type: str  # tushare, minqmt, akshare, tdx
    priority: int = 1
    enabled: bool = True
    api_key: Optional[str] = None
    api_secret: Optional[str] = None
    base_url: Optional[str] = None
    rate_limit: int = 100  # 每分钟请求限制
    timeout: int = 30
    
    # 特定数据源配置
    extra_params: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DatabaseConfig:
    """数据库配置"""
    db_type: str = "duckdb"  # duckdb, timescaledb
    db_path: str = "./data/lanbao.duckdb"
    
    # TimescaleDB配置(后续版本使用)
    host: str = "localhost"
    port: int = 5432
    username: str = "lanbao"
    password: str = ""
    database: str = "lanbao"
    
    # 连接池配置
    pool_size: int = 10
    max_overflow: int = 20


@dataclass
class StrategyConfig:
    """策略配置"""
    strategy_id: str
    strategy_name: str
    strategy_type: str  # momentum, mean_reversion, multi_factor
    symbols: List[str] = field(default_factory=list)
    parameters: Dict[str, Any] = field(default_factory=dict)
    risk_limits: Dict[str, float] = field(default_factory=dict)
    enabled: bool = True


class ConfigManager:
    """配置管理器"""
    
    def __init__(self, config_dir: str = "./config"):
        self.config_dir = Path(config_dir)
        self._configs: Dict[str, Any] = {}
        
    def load_all(self):
        """加载所有配置"""
        # 加载主配置
        main_config = self.config_dir / "lanbao.yaml"
        if main_config.exists():
            with open(main_config, 'r', encoding='utf-8') as f:
                self._configs['main'] = yaml.safe_load(f)
        
        # 加载节点配置
        nodes_dir = self.config_dir / "nodes"
        if nodes_dir.exists():
            for cfg_file in nodes_dir.glob("*.yaml"):
                node_name = cfg_file.stem
                with open(cfg_file, 'r', encoding='utf-8') as f:
                    self._configs[f'node_{node_name}'] = yaml.safe_load(f)
        
        # 加载策略配置
        strategies_dir = self.config_dir / "strategies"
        if strategies_dir.exists():
            for cfg_file in strategies_dir.glob("*.yaml"):
                strategy_name = cfg_file.stem
                with open(cfg_file, 'r', encoding='utf-8') as f:
                    self._configs[f'strategy_{strategy_name}'] = yaml.safe_load(f)
    
    def get(self, key: str, default: Any = None) -> Any:
        """获取配置项"""
        return self._configs.get(key, default)
    
    def get_node_config(self, node_name: str) -> NodeConfig:
        """获取节点配置"""
        cfg_dict = self._configs.get(f'node_{node_name}', {})
        return NodeConfig(**cfg_dict)
    
    def get_strategy_config(self, strategy_name: str) -> StrategyConfig:
        """获取策略配置"""
        cfg_dict = self._configs.get(f'strategy_{strategy_name}', {})
        return StrategyConfig(**cfg_dict)
    
    def reload(self):
        """重新加载配置"""
        self._configs.clear()
        self.load_all()


# 全局配置管理器实例
_global_config_manager: Optional[ConfigManager] = None


def get_config_manager(config_dir: str = "./config") -> ConfigManager:
    """获取全局配置管理器"""
    global _global_config_manager
    if _global_config_manager is None:
        _global_config_manager = ConfigManager(config_dir)
        _global_config_manager.load_all()
    return _global_config_manager
