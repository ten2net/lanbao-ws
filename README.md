# 揽宝智能投研交易平台 (Lanbao)

<p align="center">
  <img src="https://img.shields.io/badge/version-0.5.0-blue" alt="Version">
  <img src="https://img.shields.io/badge/ROS2-Humble-orange" alt="ROS2">
  <img src="https://img.shields.io/badge/Python-3.10-green" alt="Python">
  <img src="https://img.shields.io/badge/License-MIT-yellow" alt="License">
</p>

揽宝智能投研交易平台是一个基于 **ROS2 Humble 分布式架构** 的量化交易研究平台，为个人量化交易者和中小型投资机构提供生产级的程序化投研交易能力。

---

## 功能特性

### 核心能力

| 模块 | 功能 | 状态 |
|------|------|------|
| 数据服务 | 多源数据采集（Tushare/AKShare/通达信/QMT）、DuckDB 本地存储、自动缓存 | 可用 |
| 回测引擎 | 向量化回测、交易成本模拟、绩效指标分析 | 可用 |
| 策略系统 | 策略模板化、内置策略（MA/RSI/MACD）、策略生命周期管理 | 可用 |
| 风险控制 | 仓位限制、回撤限制、日亏损限制、熔断机制 | 可用 |
| 系统监控 | 节点健康监控、资源指标采集、告警持久化 | 可用 |
| 前端界面 | React 回测面板、Streamlit 监控大屏、Jupyter 研究环境 | 可用 |

### 数据源适配器

| 适配器 | 优先级 | 速率限制 | 说明 |
|--------|--------|----------|------|
| Tushare | 1 | 0.1s | 主数据源，需 [TUSHARE_TOKEN](https://tushare.pro/register) |
| 通达信 | 2 | — | 通达信行情服务器（如有） |
| AKShare | 3 | 3.0s | 免费替代，严格限速 |
| MiniQMT | 4 | — | 迅投 QMT 量化终端（如有） |

数据获取采用 **缓存优先 + 自动降级** 策略：先查本地 DuckDB 缓存，缓存 miss 则按优先级尝试各适配器，成功写入缓存，失败自动 fallback。

---

## 系统架构

```
+-----------------------------------------------------------------------------+
|                              揽宝智能投研平台 V0.5                            |
+-----------------------------------------------------------------------------+
|  前端层                                                                       |
|  +-------------+  +-------------+  +-------------+  +-------------+         |
|  |  React 回测  |  | Streamlit  |  | Jupyter Lab |  | ROS2 Web    |         |
|  |  管理面板    |  | 监控大屏    |  |  研究环境   |  | 桥接(9090)  |         |
|  +------+------+  +------+------+  +------+------+  +------+------+         |
|         |                |                |                |                |
+---------+----------------+----------------+----------------+----------------+
|  服务层 (ROS2 节点)                                                           |
|  +-------------+  +-------------+  +-------------+  +-------------+         |
|  | core_node   |  |market_data  |  | data_sync   |  |backtest_    |         |
|  | (协调+桥接)  |  | (数据采集)  |  | (批量同步)  |  | engine      |         |
|  +-------------+  +-------------+  +-------------+  +-------------+         |
|  +-------------+  +-------------+  +-------------+  +-------------+         |
|  | strategy_   |  | risk_       |  | monitor_    |  | system_     |         |
|  | manager     |  | control     |  | node        |  | metrics     |         |
|  | (策略管理)  |  | (风险控制)  |  | (监控告警)  |  | (资源采集)  |         |
|  +-------------+  +-------------+  +-------------+  +-------------+         |
+-----------------------------------------------------------------------------+
|  数据层                                                                       |
|  +---------------------------------------------------------------------+    |
|  | DuckDB (本地文件) | Tushare API | AKShare | 通达信 | QMT           |    |
|  +---------------------------------------------------------------------+    |
+-----------------------------------------------------------------------------+
```

### 节点通信拓扑

- **Topic 通信**: `/market/data`、`/backtest/result`、`/system/metrics`、`/risk/alert`、`/node/status`
- **Service 通信**: `GetMarketData`、`RunBacktest`、`ManageStrategy`、`CheckRisk`、`GetNodeStatus`
- **Action 通信**: `BacktestStrategy`（带进度反馈）、`DeployStrategy`

---

## 快速开始

### 环境要求

- Ubuntu 22.04 / macOS / Windows (WSL2)
- Python 3.10（与 ROS2 Humble 绑定）
- ROS2 Humble
- Docker & Docker Compose（可选）

### 方式一：Docker Compose 部署（推荐）

```bash
# 1. 克隆仓库并进入目录
cd lanbao_ws

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env，设置 TUSHARE_TOKEN（必需）

# 3. 构建并启动
docker compose build
docker compose up -d

# 4. 查看服务状态
docker compose ps

# 5. 查看日志
docker compose logs -f lanbao-core
```

启动后访问：
- Streamlit 监控大屏: http://localhost:8501
- Jupyter 研究环境: http://localhost:8888
- React 回测面板: http://localhost:8502（需单独启动前端开发服务器）
- ROS2 WebSocket: ws://localhost:9090

### 方式二：本地开发环境

```bash
# 1. 确保 ROS2 Humble 已安装
source /opt/ros/humble/setup.bash

# 2. 安装 Python 依赖（使用 uv）
uv sync  # 或 uv sync --extra dev

# 3. 构建 ROS2 包
./scripts/build.sh

# 4. 启动所有节点
./scripts/start_nodes.sh

# 5. 启动回测 API（另开终端）
./scripts/start_backtest_api.sh  # http://localhost:8000

# 6. 启动回测前端（另开终端）
./scripts/start_backtest_web.sh  # http://localhost:8502
```

停止节点：
```bash
./scripts/stop_nodes.sh
```

---

## 详细配置

### 环境变量

复制 `.env.example` 为 `.env` 并填写：

| 变量 | 必需 | 默认值 | 说明 |
|------|------|--------|------|
| `TUSHARE_TOKEN` | 是 | — | Tushare Pro API Token |
| `ROS_DOMAIN_ID` | 否 | `0` | ROS2 Domain ID（多机部署时区分） |
| `LOG_LEVEL` | 否 | `INFO` | 日志级别 |
| `DUCKDB_PATH` | 否 | `./data/lanbao.duckdb` | 数据库文件路径 |
| `LANBAO_DATA_SOURCES` | 否 | `tushare,akshare` | 启用的数据源，逗号分隔 |
| `DEFAULT_INITIAL_CAPITAL` | 否 | `100000` | 回测默认初始资金 |
| `COMMISSION_RATE` | 否 | `0.0003` | 佣金率 |
| `SLIPPAGE` | 否 | `0.001` | 滑点 |
| `MAX_POSITION_SIZE` | 否 | `0.2` | 最大仓位比例 |
| `MAX_DRAWDOWN` | 否 | `0.1` | 最大回撤限制 |
| `MAX_DAILY_LOSS` | 否 | `0.05` | 最大日亏损限制 |

### 主配置文件

`config/lanbao.yaml`：

```yaml
system:
  name: "揽宝智能投研交易平台"
  version: "0.5.0"
  environment: "development"

logging:
  level: "INFO"
  file: "./logs/lanbao.log"

data:
  duckdb:
    path: "./data/lanbao.duckdb"
  sources:
    tushare: { enabled: true, priority: 1, rate_limit: 100 }
    akshare: { enabled: false, priority: 2, rate_limit: 200 }

backtest:
  default_initial_capital: 100000.0
  commission_rate: 0.0003
  slippage: 0.001

risk:
  max_position_size: 0.2
  max_drawdown: 0.1
  max_daily_loss: 0.05
```

---

## 使用指南

### 数据获取

```python
from lanbao_data.ros2_client import ROS2Client

client = ROS2Client()

# 获取单只股票历史数据
df = client.get_market_data(
    symbol="000001.SZ",
    start_date="20240101",
    end_date="20241231",
    fields=["open", "high", "low", "close", "volume"]
)

# 批量获取股票列表
df = client.get_stock_list(exchange="SZSE")

client.shutdown()
```

### 策略开发与回测

```python
from lanbao_strategy.strategy_factory import StrategyFactory
from lanbao_backtest.ros2_client import BacktestClient

# 创建策略
factory = StrategyFactory()
strategy = factory.create_strategy(
    template_id="ma_cross",
    strategy_id="my_ma",
    name="双均线策略",
    params={"fast_period": 5, "slow_period": 20}
)

# 执行回测
client = BacktestClient()
result = client.run_backtest(
    strategy_id="my_ma",
    symbols=["000001.SZ"],
    start_date="20240101",
    end_date="20241231",
    initial_capital=100000
)

print(f"总收益: {result['total_return']:.2%}")
print(f"夏普比率: {result['sharpe_ratio']:.2f}")
print(f"最大回撤: {result['max_drawdown']:.2%}")
```

### 自定义策略

继承 `StrategyTemplate` 实现自定义策略：

```python
from lanbao_strategy.strategy_template import StrategyTemplate, Signal, SignalType

class MyStrategy(StrategyTemplate):
    def analyze(self, data):
        # 计算技术指标
        data['sma20'] = data['close'].rolling(20).mean()
        return data

    def generate_signals(self, data):
        signals = []
        if data['close'].iloc[-1] > data['sma20'].iloc[-1]:
            signals.append(Signal(
                type=SignalType.BUY,
                price=data['close'].iloc[-1],
                reason="收盘价上穿20日均线"
            ))
        return signals
```

然后在 `StrategyFactory._register_builtin_strategies()` 中注册：

```python
self.register_strategy("my_strategy", MyStrategy, "自定义策略")
```

---

## API 接口

### FastAPI 网关

回测服务提供 FastAPI HTTP 接口（端口 8000）：

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/backtests` | 回测列表 |
| POST | `/api/v1/backtests` | 创建回测 |
| GET | `/api/v1/backtests/{id}` | 回测详情 |
| DELETE | `/api/v1/backtests/{id}` | 删除回测 |
| GET | `/api/v1/strategies` | 策略模板列表 |
| GET | `/api/v1/data/stats` | 数据统计 |
| GET | `/api/v1/data/tables` | 数据表列表 |
| GET | `/api/v1/data/preview` | 表数据预览 |
| GET | `/api/v1/config` | 系统配置 |
| WS | `/ws/backtest/{task_id}` | 回测进度实时推送 |

完整 API 文档启动后访问：http://localhost:8000/docs

### ROS2 Service

| 服务名 | 请求类型 | 说明 |
|--------|----------|------|
| `GetMarketData` | `GetMarketData.Request` | 获取市场数据 |
| `RunBacktest` | `RunBacktest.Request` | 执行回测 |
| `ManageStrategy` | `ManageStrategy.Request` | 策略管理（创建/启动/暂停/停止） |
| `CheckRisk` | `CheckRisk.Request` | 风险检查 |
| `GetNodeStatus` | `GetNodeStatus.Request` | 获取节点状态 |
| `GetDataStats` | `GetDataStats.Request` | 数据统计概况 |
| `GetDataTables` | `GetDataTables.Request` | 数据表列表 |
| `GetTablePreview` | `GetTablePreview.Request` | 表数据预览 |
| `GetDataQuality` | `GetDataQuality.Request` | 数据质量检查 |
| `GetSyncStatus` | `GetSyncStatus.Request` | 数据同步状态 |

---

## 项目结构

```
lanbao_ws/
├── src/                              # ROS2 包源码
│   ├── lanbao_interfaces/            # 接口定义（msg/srv/action）
│   │   ├── msg/                      # MarketData, StockSignal, TradeSignal...
│   │   ├── srv/                      # GetMarketData, RunBacktest...
│   │   └── action/                   # BacktestStrategy, DeployStrategy...
│   ├── lanbao_core/                  # 核心框架
│   │   ├── lanbao_core/
│   │   │   ├── base_node.py          # 节点生命周期基类
│   │   │   ├── data_node.py          # 数据处理节点基类
│   │   │   ├── strategy_node.py      # 策略节点基类
│   │   │   ├── health_monitor.py     # 健康监控
│   │   │   └── metrics.py            # 指标收集
│   │   └── launch/lanbao.launch.py   # 核心启动文件
│   ├── lanbao_data/                  # 数据服务
│   │   ├── lanbao_data/
│   │   │   ├── market_data_node.py   # 市场数据节点
│   │   │   ├── data_sync_node.py     # 数据同步节点
│   │   │   ├── tushare_adapter.py    # Tushare 适配器
│   │   │   ├── akshare_adapter.py    # AKShare 适配器
│   │   │   ├── tdx_adapter.py        # 通达信适配器
│   │   │   ├── miniqmt_adapter.py    # QMT 适配器
│   │   │   └── duckdb_storage.py     # DuckDB 存储
│   ├── lanbao_strategy/              # 策略服务
│   │   ├── lanbao_strategy/
│   │   │   ├── strategy_template.py  # 策略模板基类
│   │   │   ├── strategy_factory.py   # 策略工厂
│   │   │   └── strategy_manager_node.py
│   │   └── strategies/               # 内置策略
│   │       ├── ma_cross.py           # 双均线策略
│   │       ├── rsi.py                # RSI 策略
│   │       └── macd.py               # MACD 策略
│   ├── lanbao_backtest/              # 回测服务
│   │   ├── lanbao_backtest/
│   │   │   ├── backtest_engine.py    # 向量化回测引擎
│   │   │   ├── backtest_engine_node.py
│   │   │   ├── performance_analyzer.py
│   │   │   └── api/                  # FastAPI 网关
│   │   │       ├── main.py
│   │   │       ├── routes/
│   │   │       └── services/
│   │   └── web/                      # React 前端
│   │       ├── src/
│   │       └── dist/
│   ├── lanbao_risk/                  # 风险控制
│   │   └── lanbao_risk/risk_control_node.py
│   └── lanbao_monitor/               # 监控服务
│       ├── lanbao_monitor/
│       │   ├── monitor_node.py       # 监控节点
│       │   └── system_metrics_node.py
│       └── dashboard.py              # Streamlit 大屏
├── config/                           # 配置目录
│   ├── lanbao.yaml                   # 主配置
│   └── strategies/                   # 策略配置
├── scripts/                          # 运维脚本
│   ├── build.sh                      # 构建脚本
│   ├── start_nodes.sh                # 启动所有节点
│   ├── stop_nodes.sh                 # 停止所有节点
│   ├── start_backtest_api.sh         # 启动回测 API
│   └── start_backtest_web.sh         # 启动回测前端
├── notebooks/                        # Jupyter 笔记本
│   ├── 01_quick_start.ipynb
│   └── 02_multi_data_source_demo.ipynb
├── data/                             # DuckDB 数据库
├── logs/                             # 运行日志
├── reports/                          # 回测报告
├── docker-compose.yml                # Docker Compose 生产配置
├── docker-compose.dev.yml            # Docker Compose 开发配置
├── Dockerfile                        # Docker 镜像构建
├── pyproject.toml                    # Python 项目配置
├── requirements.txt                  # Python 依赖
├── .env.example                      # 环境变量模板
└── README.md                         # 本文件
```

---

## Docker 服务清单

生产环境 `docker-compose.yml`：

| 服务 | 容器名 | 端口 | 说明 |
|------|--------|------|------|
| lanbao-core | lanbao-core | 9090 | core_node + rosbridge WebSocket |
| market-data | lanbao-market-data | — | 市场数据节点 |
| data-sync | lanbao-data-sync | — | 数据同步节点 |
| backtest-engine | lanbao-backtest | — | 回测引擎节点 |
| strategy-manager | lanbao-strategy | — | 策略管理节点 |
| risk-control | lanbao-risk | — | 风险控制节点 |
| monitor | lanbao-monitor | — | 监控节点 |
| system-metrics | lanbao-system-metrics | — | 系统指标节点 |
| jupyter | lanbao-jupyter | 8888 | Jupyter Lab |
| web | lanbao-web | 8501 | Streamlit 监控面板 |

---

## 开发指南

### 添加新 ROS2 节点

1. 在 `src/` 下创建新包（含 `setup.py`、`package.xml`、`resource/`）
2. 继承 `LanBaoBaseNode` 或专用子类
3. 实现 `initialize()`、`start()`、`stop()`
4. 在 `setup.py` 中添加 `entry_points`
5. 更新 `scripts/build.sh` 和 `scripts/start_nodes.sh`

### 添加新策略

1. 在 `src/lanbao_strategy/strategies/` 下创建新文件
2. 继承 `StrategyTemplate`，实现 `analyze()` 和 `generate_signals()`
3. 在 `StrategyFactory._register_builtin_strategies()` 中注册

### 代码规范

```bash
# 格式化
black .

# 类型检查
mypy src/

# 代码检查
flake8 src/

# 运行测试
pytest -v
```

---

## 技术栈

- **后端框架**: ROS2 Humble, Python 3.10
- **数据存储**: DuckDB, SQLAlchemy
- **数据源**: Tushare, AKShare, PyTDX
- **回测计算**: vectorbt, TA-Lib, NumPy, Pandas
- **Web 框架**: FastAPI, Uvicorn
- **前端**: React 18 + TypeScript + Vite + Ant Design 5, Streamlit
- **监控**: psutil, Loguru
- **部署**: Docker, Docker Compose

---

## 开发计划

| 版本 | 目标 | 状态 |
|------|------|------|
| V0.5 MVP | 验证核心架构，基础回测交易 | 当前版本 |
| V1.0 | 核心交易功能，实盘模拟 | 计划中 |
| V1.5 | 稳定性和性能优化 | 计划中 |
| V2.0 | 完整功能体系 | 计划中 |
| V3.0 | 企业级部署 | 计划中 |

---

## 许可证

本项目采用 [MIT License](LICENSE) 开源协议。

## 联系方式

- 邮箱: dev@lanbao.com
- 项目地址: https://github.com/lanbao/lanbao-trading

---

**免责声明**: 本软件仅供研究和学习使用，不构成任何投资建议。过往回测表现不代表未来收益，使用者应自行承担所有投资风险。
