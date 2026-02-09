# 揽宝智能投研交易平台 V0.5 (MVP)

揽宝智能投研交易平台是一个基于ROS2分布式架构的量化投研交易系统，为个人量化交易者和中小型投资机构提供生产级的程序化投研交易能力。

## 功能特性

### MVP版本功能范围

```
┌─────────────────────────────────────────────────────────┐
│                   V0.5 MVP 功能范围                      │
├─────────────────────────────────────────────────────────┤
│ 数据层: Tushare数据源 + DuckDB基础存储                    │
│ 计算层: 单节点回测引擎 + 基础策略模板                      │
│ 界面层: Jupyter研究环境 + 基础Web监控                     │
│ 部署: 单机Docker部署                                     │
└─────────────────────────────────────────────────────────┘
```

### 核心功能

- **数据服务**: 集成Tushare数据源，支持A股历史数据获取和DuckDB本地存储
- **回测引擎**: 向量化回测引擎，支持双均线、RSI、MACD等基础策略
- **策略管理**: 策略生命周期管理，支持策略创建、启动、暂停、停止
- **风险控制**: 基础风控规则，包括仓位限制、回撤限制、熔断机制
- **系统监控**: 节点健康监控和系统资源监控
- **研究环境**: Jupyter Notebook研究环境

## 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                 揽宝智能投研交易平台 V0.5                   │
├─────────────────────────────────────────────────────────────┤
│ 应用层: Jupyter研究环境 │ 基础Web监控                         │
├─────────────────────────────────────────────────────────────┤
│ 服务层: 策略工厂 │ 回测引擎 │ 风控中心 │ 运维平台            │
├─────────────────────────────────────────────────────────────┤
│ 框架层: ROS2分布式框架 + 事件驱动机制                        │
├─────────────────────────────────────────────────────────────┤
│ 数据层: DuckDB本地存储 + Tushare数据源                       │
├─────────────────────────────────────────────────────────────┤
│ 基础设施: Docker容器化部署                                  │
└─────────────────────────────────────────────────────────────┘
```

### ROS2节点架构

| 节点名称 | 核心职责 | 状态 |
|---------|---------|------|
| `market_data_node` | 市场数据获取和存储 | ✅ |
| `backtest_engine_node` | 策略回测引擎 | ✅ |
| `strategy_manager_node` | 策略生命周期管理 | ✅ |
| `risk_control_node` | 实时风险控制 | ✅ |
| `monitor_node` | 系统监控告警 | ✅ |

## 快速开始

### 环境要求

- Ubuntu 22.04 LTS
- ROS2 Humble
- Python 3.10+
- Docker & Docker Compose (可选)

### 安装步骤

1. **克隆项目**
```bash
cd ~/lanbao_ws
```

2. **安装Python依赖**
```bash
pip install -r requirements.txt
```

3. **配置环境变量**
```bash
cp .env.example .env
# 编辑 .env 文件，填写 TUSHARE_TOKEN
```

4. **构建ROS2包**
```bash
./scripts/build.sh
```

5. **启动系统**
```bash
./scripts/start_nodes.sh
```

### Docker部署

```bash
# 设置环境变量
export TUSHARE_TOKEN=your_token_here

# 启动所有服务
docker-compose up -d

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down
```

## 使用指南

### 1. 数据获取

```python
from lanbao_data.tushare_adapter import TushareAdapter

tushare = TushareAdapter()
data = tushare.get_daily_data("000001.SZ", start_date="20230101", end_date="20241231")
```

### 2. 策略开发

```python
from lanbao_strategy.strategy_template import MovingAverageCrossStrategy

strategy = MovingAverageCrossStrategy(
    strategy_id="ma_demo",
    name="双均线策略",
    fast_period=5,
    slow_period=20
)

signals = strategy.generate_signals(data)
```

### 3. 回测

```python
from lanbao_backtest.backtest_engine import BacktestEngine, BacktestConfig

config = BacktestConfig(initial_capital=100000)
engine = BacktestEngine(config)

result = engine.run_backtest(
    strategy_id="ma_cross",
    symbol="000001.SZ",
    data=data,
    signal_generator=ma_cross_signal
)

print(f"总收益: {result.total_return:.2%}")
print(f"夏普比率: {result.sharpe_ratio:.2f}")
```

### 4. Jupyter研究

```bash
jupyter lab notebooks/
```

参考 `notebooks/01_quick_start.ipynb` 进行策略研究。

## 项目结构

```
lanbao_ws/
├── config/                 # 配置文件
│   ├── lanbao.yaml        # 主配置
│   └── strategies/        # 策略配置
├── data/                   # 数据目录
├── docs/                   # 文档
├── logs/                   # 日志目录
├── notebooks/              # Jupyter笔记本
├── scripts/                # 脚本
│   ├── build.sh           # 构建脚本
│   ├── start_nodes.sh     # 启动脚本
│   └── stop_nodes.sh      # 停止脚本
├── src/                    # 源代码
│   ├── lanbao_core/       # 核心框架
│   ├── lanbao_data/       # 数据服务
│   ├── lanbao_strategy/   # 策略服务
│   ├── lanbao_backtest/   # 回测引擎
│   ├── lanbao_risk/       # 风险控制
│   └── lanbao_monitor/    # 监控服务
├── Dockerfile             # Docker镜像
├── docker-compose.yml     # Docker Compose配置
├── requirements.txt       # Python依赖
└── README.md              # 本文件
```

## 开发计划

| 版本 | 目标 | 时间 |
|------|------|------|
| V0.5 MVP | 验证核心架构，基础回测交易 | ✅ 当前 |
| V1.0 | 核心交易功能，实盘模拟 | 计划中 |
| V1.5 | 稳定性和性能优化 | 计划中 |
| V2.0 | 完整功能体系 | 计划中 |
| V3.0 | 企业级部署 | 计划中 |

## 贡献指南

欢迎提交Issue和PR！

## 许可证

MIT License

## 联系方式

- 邮箱: dev@lanbao.com
- 项目地址: https://github.com/lanbao/lanbao-trading

---

**免责声明**: 本系统仅供研究和学习使用，不构成任何投资建议。使用本系统进行交易产生的盈亏由用户自行承担。
