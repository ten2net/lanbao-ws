# Lanbao Workspace (揽宝智能投研交易平台)

## Project Overview

揽宝智能投研交易平台 V0.5 (MVP) 是一个基于ROS2分布式架构的量化投研交易系统。

### 核心特性
- **数据层**: Tushare数据源 + DuckDB基础存储
- **计算层**: 单节点回测引擎 + 基础策略模板
- **界面层**: Jupyter研究环境 + 基础Web监控
- **部署**: 单机Docker部署

## 系统架构

### ROS2节点清单

| 节点名称 | 包名 | 核心职责 | 入口函数 |
|---------|------|---------|---------|
| `market_data_node` | lanbao_data | 市场数据获取和存储 | `lanbao_data.market_data_node:main` |
| `backtest_engine_node` | lanbao_backtest | 策略回测引擎 | `lanbao_backtest.backtest_engine_node:main` |
| `strategy_manager_node` | lanbao_strategy | 策略生命周期管理 | `lanbao_strategy.strategy_manager_node:main` |
| `risk_control_node` | lanbao_risk | 实时风险控制 | `lanbao_risk.risk_control_node:main` |
| `monitor_node` | lanbao_monitor | 系统监控告警 | `lanbao_monitor.monitor_node:main` |

### 消息/服务/动作接口

#### 消息 (msg)
- `MarketData` - 市场数据
- `StockSignal` - 股票信号
- `TradeSignal` - 交易信号
- `OrderStatus` - 订单状态
- `PortfolioStatus` - 持仓状态
- `RiskAlert` - 风险告警
- `BacktestResult` - 回测结果
- `StrategyStatus` - 策略状态
- `NodeStatus` - 节点状态

#### 服务 (srv)
- `GetMarketData` - 获取市场数据
- `ExecuteOrder` - 执行订单
- `RunBacktest` - 运行回测
- `ManageStrategy` - 管理策略
- `CheckRisk` - 风险检查
- `GetNodeStatus` - 获取节点状态

#### 动作 (action)
- `BacktestStrategy` - 回测策略
- `DeployStrategy` - 部署策略
- `CircuitBreaker` - 熔断操作

## 项目结构

```
lanbao_ws/
├── config/              # 配置文件
├── data/                # 数据目录 (DuckDB)
├── docs/                # 项目文档
├── logs/                # 日志目录
├── notebooks/           # Jupyter笔记本
├── scripts/             # 构建/启动脚本
├── src/                 # ROS2包源码
│   ├── lanbao_interfaces/  # 接口定义
│   ├── lanbao_core/        # 核心框架
│   ├── lanbao_data/        # 数据服务
│   ├── lanbao_strategy/    # 策略服务
│   ├── lanbao_backtest/    # 回测引擎
│   ├── lanbao_risk/        # 风险控制
│   └── lanbao_monitor/     # 监控服务
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── README.md
```

## 构建和运行

### 构建命令
```bash
./scripts/build.sh
# 或手动:
source /opt/ros/humble/setup.bash
colcon build --packages-select lanbao_interfaces lanbao_core lanbao_data lanbao_strategy lanbao_backtest lanbao_risk lanbao_monitor
```

### 启动命令
```bash
# 方式1: 使用脚本
./scripts/start_nodes.sh

# 方式2: 手动启动
source /opt/ros/humble/setup.bash
source install/setup.bash
ros2 run lanbao_data market_data_node &
ros2 run lanbao_backtest backtest_engine_node &
ros2 run lanbao_strategy strategy_manager_node &
ros2 run lanbao_risk risk_control_node &
ros2 run lanbao_monitor monitor_node &

# 方式3: Docker
docker-compose up -d
```

### 停止命令
```bash
./scripts/stop_nodes.sh
# 或
docker-compose down
```

## 开发指南

### 添加新策略
1. 在 `src/lanbao_strategy/lanbao_strategy/strategy_template.py` 中继承 `StrategyTemplate`
2. 实现 `analyze()` 和 `generate_signals()` 方法
3. 在 `StrategyFactory` 中注册新策略

### 添加新节点
1. 在 `src/` 下创建新包
2. 继承 `LanBaoBaseNode` 或相应基类
3. 实现 `initialize()`, `start()`, `stop()` 方法
4. 在 `setup.py` 中添加入口点

## 环境变量

| 变量名 | 说明 | 必需 |
|-------|------|------|
| `TUSHARE_TOKEN` | Tushare API Token | 是 |
| `DUCKDB_PATH` | DuckDB数据库路径 | 否 |
| `ROS_DOMAIN_ID` | ROS2 Domain ID | 否 |
| `LOG_LEVEL` | 日志级别 | 否 |

## 技术栈

- **框架**: ROS2 Humble
- **语言**: Python 3.10+
- **数据源**: Tushare
- **数据库**: DuckDB
- **容器**: Docker, Docker Compose
- **研究环境**: Jupyter Lab
- **PYTHON包管理工具**: uv

## 相关文档

- `docs/揽宝智能投研交易平台架构设计.md` - 架构设计文档
- `docs/揽宝系统版本迭代计划.md` - 版本迭代计划
- `notebooks/01_quick_start.ipynb` - 快速入门教程

---
*Last updated: 2026-02-09*
*Version: 0.5.0 (MVP)*
