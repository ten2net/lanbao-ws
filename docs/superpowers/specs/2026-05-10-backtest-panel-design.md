# 揽宝智能投研平台 — 专业回测管理与分析面板设计文档

**版本**: v1.0  
**日期**: 2026-05-10  
**状态**: 已评审，待实现  

---

## 1. 概述

### 1.1 背景

当前揽宝平台的 Streamlit Dashboard 回测结果面板功能过于简单，仅包含基础表格、收益对比柱状图和风险收益散点图。随着策略开发和回测需求的增长，需要一个专业级别的回测管理与分析面板，支持丰富的分析图表、交易明细穿透、批量对比和参数敏感性分析。

### 1.2 设计目标

- **回测管理**：支持筛选、排序、标签分组、批量操作
- **分析图表**：权益曲线、回撤曲线、月度收益热力图、K线+买卖点标注
- **交易明细**：逐笔交易记录、买卖点标注在K线图上
- **批量对比**：多策略收益曲线叠加、指标并排对比
- **参数分析**：同一策略不同参数组合批量回测，热力图展示
- **实时反馈**：回测执行进度实时推送

### 1.3 设计约束

- 现有 Streamlit Dashboard 保留，回测面板作为独立应用
- 继续使用 ROS2 分布式架构，不破坏现有节点通信
- 数据持久化使用增强版 JSON 文件（不引入新数据库）
- 前端使用 React + TradingView Lightweight Charts
- 后端使用 FastAPI 作为 ROS2 网关

---

## 2. 系统架构与部署拓扑

### 2.1 整体架构

```
┌─────────────────────────────────────────────────────────────┐
│                        用户浏览器                            │
│   Streamlit Dashboard (localhost:8501)                      │
│   └─ 系统概览 / 数据底座 / 风险监控 / 节点状态               │
│                                                             │
│   React Backtest Panel (localhost:8502)                     │
│   └─ 回测列表 / 回测详情 / 批量对比 / 参数分析              │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼ REST API / WebSocket
┌─────────────────────────────────────────────────────────────┐
│              FastAPI Backend Gateway (localhost:8000)       │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              ROS2 Client Manager                     │   │
│  │  (单例模式，维护与 ROS2 的连接生命周期)               │   │
│  └─────────────────────────────────────────────────────┘   │
│                          │                                  │
│          ┌───────────────┼───────────────┐                 │
│          ▼               ▼               ▼                 │
│   ┌──────────┐    ┌──────────┐    ┌──────────┐            │
│   │ Service  │    │  Action  │    │  Topic   │            │
│   │  Client  │    │  Client  │    │ Subscriber│            │
│   └────┬─────┘    └────┬─────┘    └────┬─────┘            │
│        │               │               │                    │
│        ▼               ▼               ▼                    │
│   backtest/run    backtest/strategy  /backtest/result      │
│   backtest/status    (进度反馈)      /backtest/progress    │
│   (快速回测)        (长时回测)       (结果/进度广播)        │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼ ROS2 DDS
┌─────────────────────────────────────────────────────────────┐
│                     ROS2 分布式节点层                         │
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ backtest_eng │  │ market_data  │  │  monitor_    │      │
│  │ ine_node     │  │ _node        │  │  node        │      │
│  │              │  │              │  │              │      │
│  │ • ActionSrv  │  │ • Service    │  │ • Service    │      │
│  │   backtest/  │  │   market_    │  │   monitor/   │      │
│  │   strategy   │  │   data/get   │  │   nodes      │      │
│  │              │  │              │  │              │      │
│  │ • Service    │  │              │  │ • Topic Pub  │      │
│  │   backtest/  │  │              │  │   /node_     │      │
│  │   run        │  │              │  │   status     │      │
│  │              │  │              │  │              │      │
│  │ • Service    │  │              │  │              │      │
│  │   backtest/  │  │              │  │              │      │
│  │   status     │  │              │  │              │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                     数据持久化层                              │
│  reports/                                                   │
│  ├─ bt_xxx.json          ── 回测结果元数据 + 绩效指标        │
│  ├─ bt_xxx.html          ── HTML 可视化报告                  │
│  ├─ bt_xxx.equity.json   ── 权益曲线时间序列                 │
│  ├─ bt_xxx.trades.json   ── 交易明细                        │
│  └─ bt_xxx.monthly.json  ── 月度收益矩阵                     │
│                                                             │
│  data/lanbao.duckdb      ── 行情数据源                      │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 部署方式

| 组件 | 端口 | 启动命令 |
|------|------|----------|
| Streamlit Dashboard | 8501 | `streamlit run src/lanbao_monitor/dashboard.py --server.port 8501` |
| FastAPI Backend | 8000 | `uvicorn src/lanbao_backtest/api/backtest_api:app --host 0.0.0.0 --port 8000 --reload` |
| React Frontend | 8502 | `cd src/lanbao_backtest/web && npm run dev` |

### 2.3 ROS2 通信机制职责划分

| ROS2 机制 | 用途 | 场景 |
|-----------|------|------|
| **Action** (`backtest/strategy`) | 长时间回测执行 | 数据量大、计算耗时长的回测，支持实时进度反馈和取消 |
| **Service** (`backtest/run`) | 快速回测执行 | 轻量级回测，同步等待结果 |
| **Service** (`backtest/status`) | 查询回测状态 | 前端轮询或页面刷新时获取进行中的回测状态 |
| **Topic** (`/backtest/result`) | 回测结果广播 | 回测完成后自动发布，FastAPI 订阅并持久化 |
| **Topic** (`/backtest/progress`) | 进度广播 | Action 执行过程中实时发布进度百分比 |

### 2.4 Action vs Service 自动选择

FastAPI 根据回测日期范围的天数自动选择通信机制：

- **≤ 180 天** → `backtest/run` Service（同步，快速返回）
- **> 180 天** → `backtest/strategy` Action（异步，支持进度）

---

## 3. 前端页面与路由设计

### 3.1 路由结构

| 路由 | 页面 | 说明 |
|------|------|------|
| `/` | 回测列表页 | 默认 landing，展示所有回测结果 |
| `/backtest/:backtestId` | 回测详情页 | 单个回测的完整分析 |
| `/compare` | 批量对比页 | 多回测并排对比 |
| `/param-analysis` | 参数敏感性分析页 | 参数扫描热力图 |

### 3.2 统一布局 Shell

```
┌────────────────────────────────────────────────────────────┐
│  🏠 揽宝回测平台    [回测列表] [批量对比] [参数分析]  [刷新] │
├────────────┬───────────────────────────────────────────────┤
│            │                                               │
│  筛选面板   │              主内容区                          │
│            │                                               │
│  ▼ 策略类型 │                                               │
│  ☑ ma_cross│                                               │
│  ☑ rsi     │                                               │
│  ☑ macd    │                                               │
│            │                                               │
│  ▼ 标签     │                                               │
│  [优化]    │                                               │
│  [验证]    │                                               │
│  [对比]    │                                               │
│            │                                               │
│  ▼ 日期范围 │                                               │
│  2024-01   │                                               │
│  ~ 2024-12 │                                               │
│            │                                               │
├────────────┴───────────────────────────────────────────────┤
│  © 揽宝智能投研平台 v0.6.0                                  │
└────────────────────────────────────────────────────────────┘
```

### 3.3 回测列表页 (`/`)

**核心功能**：
- 表格展示所有回测结果（支持排序、分页、多选）
- 每行显示：回测ID、策略、标的、日期范围、总收益、年化收益、夏普比率、最大回撤、标签
- 顶部操作栏：批量对比（选中后跳转）、删除、导出、运行新回测（弹窗）
- 行内操作：查看详情、下载报告

**交互细节**：
- 点击行展开预览卡片（迷你权益曲线 + 关键指标）
- 拖拽表头自定义列顺序
- 标签支持点击筛选

### 3.4 回测详情页 (`/backtest/:backtestId`)

**顶部信息栏**：
```
[策略: ma_cross] [标的: 000001.SZ] [周期: 2024-01-01 ~ 2024-12-31]
总收益: +15.2%  |  年化: +18.5%  |  夏普: 1.45  |  最大回撤: -8.5%  |  交易次数: 45
```

**Tab 切换**：

| Tab | 内容 |
|-----|------|
| **📈 权益曲线** | TradingView Lightweight Charts 绘制权益曲线 + 回撤阴影区域 |
| **🕯️ K线交易** | K 线图 + 买卖点标注（绿色三角形买入，红色三角形卖出），hover 显示交易详情 |
| **📊 月度收益** | 月度收益热力图（12个月 × 多年，颜色编码正负） |
| **📝 交易明细** | 逐笔交易表格（日期、方向、价格、数量、盈亏、手续费） |
| **📋 统计指标** | 完整指标卡片网格（胜率、盈亏比、平均持仓天数、最大单笔盈利/亏损等） |

### 3.5 批量对比页 (`/compare`)

- **收益曲线叠加**：多条权益曲线在同一坐标系中对比
- **指标雷达图**：多维度对比（收益、风险、稳定性、胜率等）
- **指标对比表**：并排显示所有选中回测的关键指标
- **回撤对比**：多条回撤曲线叠加

### 3.6 参数敏感性分析页 (`/param-analysis`)

**配置区**：
- 选择策略模板
- 选择参数维度（如 ma_cross 的 fast_period × slow_period）
- 设置参数范围（fast: 3-20, slow: 10-60）
- 选择标的和日期范围

**结果区**：
- **热力图**：X轴参数1，Y轴参数2，颜色映射夏普比率/总收益
- **最优参数标记**：热力图上标注最优组合
- **TOP 10 表格**：按指标排序的前10组参数及绩效

### 3.7 前端技术选型

| 用途 | 库 |
|------|-----|
| UI 组件 | Ant Design 5.x |
| 路由 | React Router 6 |
| 状态管理 | Zustand |
| HTTP 请求 | TanStack Query (React Query) |
| K 线图 | TradingView Lightweight Charts |
| 图表 | Recharts + ECharts |
| 构建工具 | Vite |

---

## 4. 后端 API 设计

### 4.1 API 端点一览

```
┌─────────────────────────────────────────────────────────────┐
│  回测管理 API                                                │
├─────────────────────────────────────────────────────────────┤
│  GET    /api/v1/backtests              获取回测列表          │
│  GET    /api/v1/backtests/:id          获取单个回测详情      │
│  DELETE /api/v1/backtests/:id          删除回测              │
│  POST   /api/v1/backtests/:id/tags     添加/删除标签         │
│  POST   /api/v1/backtests/compare      批量对比数据          │
├─────────────────────────────────────────────────────────────┤
│  回测执行 API                                                │
├─────────────────────────────────────────────────────────────┤
│  POST   /api/v1/backtest/run           执行单个回测          │
│  POST   /api/v1/backtest/batch         批量参数扫描回测      │
│  GET    /api/v1/backtest/:id/status    查询回测执行状态      │
│  POST   /api/v1/backtest/:id/cancel    取消进行中的回测      │
├─────────────────────────────────────────────────────────────┤
│  回测分析 API                                                │
├─────────────────────────────────────────────────────────────┤
│  GET    /api/v1/backtests/:id/equity   获取权益曲线数据      │
│  GET    /api/v1/backtests/:id/trades   获取交易明细          │
│  GET    /api/v1/backtests/:id/drawdown 获取回撤序列          │
│  GET    /api/v1/backtests/:id/monthly  获取月度收益          │
│  GET    /api/v1/backtests/:id/stats    获取完整统计指标      │
├─────────────────────────────────────────────────────────────┤
│  策略管理 API                                                │
├─────────────────────────────────────────────────────────────┤
│  GET    /api/v1/strategies             获取策略模板列表      │
│  GET    /api/v1/strategies/:id/params  获取策略参数默认值    │
├─────────────────────────────────────────────────────────────┤
│  实时通信 API                                                │
├─────────────────────────────────────────────────────────────┤
│  WS     /api/v1/ws/backtest/:id        WebSocket 进度推送    │
└─────────────────────────────────────────────────────────────┘
```

### 4.2 请求/响应示例

**POST /api/v1/backtest/run** — 执行回测

```json
// Request
{
  "strategy_id": "ma_cross",
  "symbol": "000001.SZ",
  "start_date": "20240101",
  "end_date": "20241231",
  "params": {
    "fast_period": 5,
    "slow_period": 20,
    "initial_capital": 100000,
    "commission_rate": 0.0003,
    "slippage": 0.001
  }
}

// Response (Action 模式)
{
  "task_id": "bt_ma_cross_20250115_103022",
  "status": "queued",
  "estimated_duration": "30s",
  "ws_url": "/api/v1/ws/backtest/bt_ma_cross_20250115_103022"
}

// Response (Service 模式)
{
  "backtest_id": "bt_ma_cross_20250115_103022",
  "status": "completed",
  "result": {
    "total_return": 15.2,
    "annual_return": 18.5,
    "sharpe_ratio": 1.45,
    "max_drawdown": -8.5,
    "win_rate": 62.5,
    "trade_count": 45
  }
}
```

**GET /api/v1/backtests** — 回测列表

```json
// Query Params: ?strategy=ma_cross&symbol=000001.SZ&tag=优化&sort=-created_at&page=1&limit=20

// Response
{
  "total": 156,
  "page": 1,
  "limit": 20,
  "items": [
    {
      "backtest_id": "bt_ma_cross_20250115_103022",
      "strategy_name": "双均线交叉策略",
      "strategy_id": "ma_cross",
      "symbol": "000001.SZ",
      "symbol_name": "平安银行",
      "start_date": "2024-01-01",
      "end_date": "2024-12-31",
      "total_return": 15.2,
      "annual_return": 18.5,
      "sharpe_ratio": 1.45,
      "max_drawdown": -8.5,
      "win_rate": 62.5,
      "trade_count": 45,
      "tags": ["优化", "2025Q1"],
      "status": "completed",
      "created_at": "2025-01-15T10:30:22Z",
      "duration_seconds": 28.5
    }
  ]
}
```

**GET /api/v1/backtests/:id/trades** — 交易明细

```json
// Response
{
  "backtest_id": "bt_ma_cross_20250115_103022",
  "trades": [
    {
      "trade_id": "bt_ma_cross_20250115_103022_0",
      "trade_date": "2024-03-15",
      "action": "BUY",
      "quantity": 1000,
      "price": 12.50,
      "amount": 12500.00,
      "commission": 3.75,
      "pnl": null
    },
    {
      "trade_id": "bt_ma_cross_20250115_103022_1",
      "trade_date": "2024-06-20",
      "action": "SELL",
      "quantity": 1000,
      "price": 14.20,
      "amount": 14200.00,
      "commission": 4.26,
      "pnl": 1691.99
    }
  ]
}
```

### 4.3 WebSocket 实时进度

```
WS /api/v1/ws/backtest/:task_id

// 服务端推送消息格式
{"type": "progress", "progress": 0.10, "status": "获取市场数据", "timestamp": 1705311022}
{"type": "progress", "progress": 0.50, "status": "执行回测计算", "timestamp": 1705311050}
{"type": "progress", "progress": 0.80, "status": "计算绩效指标", "timestamp": 1705311075}
{"type": "completed", "backtest_id": "bt_xxx", "result": {...}, "timestamp": 1705311080}

// 失败时
{"type": "error", "message": "无法获取 000001.SZ 的市场数据", "timestamp": 1705311025}
```

### 4.4 错误响应统一格式

```json
{
  "error": {
    "code": "BACKTEST_DATA_NOT_FOUND",
    "message": "无法获取 000001.SZ 在 20240101 ~ 20241231 的市场数据",
    "details": {
      "symbol": "000001.SZ",
      "start_date": "20240101",
      "end_date": "20241231"
    }
  }
}
```

---

## 5. 数据模型

### 5.1 文件存储结构

```
reports/
├── bt_ma_cross_000001_20250115_103022.json          # 回测结果元数据 + 指标
├── bt_ma_cross_000001_20250115_103022.html          # HTML 可视化报告
├── bt_ma_cross_000001_20250115_103022.equity.json   # 权益曲线时间序列（大文件分离）
├── bt_ma_cross_000001_20250115_103022.trades.json   # 交易明细
└── bt_ma_cross_000001_20250115_103022.monthly.json  # 月度收益矩阵
```

**分离存储的原因**：权益曲线可能有数千个数据点，如果全部塞进主 JSON，会导致文件过大（>1MB），影响列表页加载速度。分离后列表页只加载轻量主文件，详情页按需加载时间序列。

### 5.2 主文件 Schema（`*.json`）

```json
{
  "schema_version": "2.0",
  "backtest_id": "bt_ma_cross_000001_20250115_103022",
  "meta": {
    "strategy_id": "ma_cross",
    "strategy_name": "双均线交叉策略",
    "strategy_params": {
      "fast_period": 5,
      "slow_period": 20,
      "initial_capital": 100000,
      "commission_rate": 0.0003,
      "slippage": 0.001
    },
    "symbol": "000001.SZ",
    "symbol_name": "平安银行",
    "start_date": "2024-01-01",
    "end_date": "2024-12-31",
    "total_trading_days": 242,
    "created_at": "2025-01-15T10:30:22Z",
    "duration_seconds": 28.5,
    "status": "completed",
    "tags": ["优化", "2025Q1"],
    "data_source": "tushare"
  },
  "performance": {
    "returns": {
      "total_return_pct": 15.2,
      "annual_return_pct": 18.5,
      "daily_return_mean_pct": 0.07,
      "daily_return_std_pct": 1.2,
      "best_day_pct": 4.5,
      "worst_day_pct": -3.2,
      "positive_days": 142,
      "negative_days": 100
    },
    "risk": {
      "sharpe_ratio": 1.45,
      "sortino_ratio": 1.62,
      "max_drawdown_pct": -8.5,
      "max_drawdown_duration_days": 18,
      "volatility_annual_pct": 12.8,
      "var_95_pct": -1.8,
      "calmar_ratio": 2.18
    },
    "trades": {
      "total_count": 45,
      "winning_count": 28,
      "losing_count": 17,
      "win_rate_pct": 62.2,
      "profit_factor": 1.67,
      "avg_trade_return_pct": 0.34,
      "avg_win_pct": 1.85,
      "avg_loss_pct": -1.12,
      "largest_win_pct": 5.2,
      "largest_loss_pct": -3.8,
      "avg_holding_days": 5.4
    }
  },
  "files": {
    "equity": "bt_ma_cross_000001_20250115_103022.equity.json",
    "trades": "bt_ma_cross_000001_20250115_103022.trades.json",
    "monthly": "bt_ma_cross_000001_20250115_103022.monthly.json"
  }
}
```

### 5.3 权益曲线文件（`*.equity.json`）

```json
{
  "backtest_id": "bt_ma_cross_000001_20250115_103022",
  "series": [
    {"date": "2024-01-02", "equity": 100000.0, "drawdown_pct": 0.0, "daily_return_pct": 0.0},
    {"date": "2024-01-03", "equity": 100150.0, "drawdown_pct": 0.0, "daily_return_pct": 0.15},
    {"date": "2024-01-04", "equity": 99800.0, "drawdown_pct": -0.35, "daily_return_pct": -0.35}
  ]
}
```

### 5.4 交易明细文件（`*.trades.json`）

```json
{
  "backtest_id": "bt_ma_cross_000001_20250115_103022",
  "trades": [
    {
      "trade_id": "bt_xxx_0",
      "trade_date": "2024-03-15",
      "action": "BUY",
      "quantity": 1000,
      "price": 12.50,
      "amount": 12500.00,
      "commission": 3.75,
      "slippage_cost": 12.50,
      "total_cost": 12516.25,
      "pnl": null,
      "pnl_pct": null
    },
    {
      "trade_id": "bt_xxx_1",
      "trade_date": "2024-06-20",
      "action": "SELL",
      "quantity": 1000,
      "price": 14.20,
      "amount": 14200.00,
      "commission": 4.26,
      "slippage_cost": 14.20,
      "total_cost": 14218.46,
      "pnl": 1681.54,
      "pnl_pct": 13.45
    }
  ]
}
```

### 5.5 月度收益文件（`*.monthly.json`）

```json
{
  "backtest_id": "bt_ma_cross_000001_20250115_103022",
  "matrix": {
    "2024": {
      "01": 2.5, "02": -1.2, "03": 3.8, "04": 1.5,
      "05": -0.8, "06": 4.2, "07": 2.1, "08": -2.5,
      "09": 1.8, "10": 3.5, "11": -1.0, "12": 2.3
    }
  }
}
```

### 5.6 向后兼容策略

现有 v1.0 JSON 文件（`backtest_id`, `strategy_name`, `total_return` 等扁平字段）仍能读取，FastAPI 加载时自动检测 `schema_version` 字段：

- 无 `schema_version` → v1.0，按需补充默认值
- `schema_version: "2.0"` → 使用完整结构

### 5.7 回测引擎输出改造

`BacktestEngineNode._save_backtest_result()` 需要输出 v2.0 格式：

1. 计算并写入主文件（元数据 + 绩效指标）
2. 序列化权益曲线到 `.equity.json`
3. 序列化交易明细到 `.trades.json`
4. 序列化月度收益到 `.monthly.json`

---

## 6. ROS2 集成细节

### 6.1 ROS2 Client Manager

FastAPI 启动时初始化一个全局的 `ROS2ClientManager`，负责维护与 ROS2 的连接生命周期：

- 单例模式，确保只有一个 rclpy 上下文
- 使用 `MultiThreadedExecutor` 支持并发 Service/Action 调用
- FastAPI 生命周期（`lifespan`）中初始化连接，关闭时断开

### 6.2 Service 调用（快速回测）

用于 ≤180 天的回测请求：

1. 获取或创建 `backtest/run` Service 客户端
2. 等待服务可用（超时 5 秒）
3. 构建 `RunBacktest.Request`
4. 异步调用，等待响应（超时 60 秒）
5. 解析响应，返回结果

### 6.3 Action 调用（长时间回测 + 进度反馈）

用于 >180 天的回测请求：

1. 创建 `backtest/strategy` Action 客户端
2. 构建 `BacktestStrategy.Goal`
3. 发送 Goal，注册 Feedback 回调
4. Feedback 通过 WebSocket 桥接推送到前端
5. 等待 Result（超时 300 秒）
6. 返回最终结果

### 6.4 Topic 订阅（回测结果自动持久化）

FastAPI 启动时注册 Topic 订阅器：

- 订阅 `/backtest/result` Topic
- 接收 `BacktestResultMsg` 消息
- 自动转换为 v2.0 JSON 格式并持久化到文件
- 日志记录持久化结果

### 6.5 WebSocket ↔ ROS2 进度桥接

`BacktestProgressBridge` 管理前端 WebSocket 连接和 ROS2 Action Feedback 之间的映射：

- 注册 WebSocket 连接时创建 Feedback 回调
- Action Feedback 触发时通过 WebSocket 推送进度消息
- 支持连接断开清理

### 6.6 集成流程

```
前端调用 POST /api/v1/backtest/run
        │
        ▼
FastAPI 判断日期范围
        │
    ┌───┴───┐
    ▼       ▼
 ≤180天   >180天
    │       │
    ▼       ▼
 Service   Action
 backtest/ backtest/
 run       strategy
    │       │
    ▼       ▼
 ROS2    ROS2 + WebSocket
 节点     进度推送
    │       │
    └───────┘
        │
        ▼
 回测引擎执行
        │
        ▼
 Topic /backtest/result
    │
    ▼
 FastAPI 订阅器
    │
    ▼
 持久化到 JSON
    │
    ▼
 前端刷新列表
```

---

## 7. 错误处理与状态管理

### 7.1 前端状态管理（Zustand）

使用 Zustand 管理全局状态：

- **回测列表**：backtests、selectedIds、filters、sorting、pagination
- **加载状态**：isLoadingList、isLoadingDetail、isRunningBacktest
- **错误状态**：error（类型和消息）
- **实时任务**：activeTasks（任务ID → 进度、状态、WebSocket连接）

### 7.2 加载状态设计

| 场景 | UI 反馈 |
|------|---------|
| 列表页首次加载 | 骨架屏（Skeleton）占位 |
| 列表页刷新/筛选 | 表格顶部进度条，数据渐变替换 |
| 详情页加载 | 左侧信息栏立即显示（列表缓存），右侧图表区域 spinner |
| 回测执行中 | 全局 toast + 可点击跳转进度详情 |
| WebSocket 断开 | 自动重连（最多3次），失败提示刷新 |

### 7.3 错误处理策略

| 错误码 | 场景 | 前端处理 |
|--------|------|----------|
| `ROS2_SERVICE_UNAVAILABLE` | ROS2 服务未启动 | 提示启动 backtest_engine_node |
| `ROS2_ACTION_TIMEOUT` | Action 执行超时 | 提示缩短日期范围或检查数据 |
| `MARKET_DATA_NOT_FOUND` | 无历史数据 | 提示检查股票代码 |
| `BACKTEST_CALCULATION_ERROR` | 回测计算异常 | 提示检查策略参数 |
| `FILE_NOT_FOUND` | 回测结果文件丢失 | 提示文件可能已被删除 |

### 7.4 乐观更新

- **回测删除**：点击删除后立即从列表移除，后端失败则恢复
- **标签添加**：输入标签后立即显示，后端失败则回滚

### 7.5 空状态设计

| 页面 | 空状态 |
|------|--------|
| 回测列表（无数据） | 插画 + "暂无回测记录" + "运行第一个回测" 按钮 |
| 回测列表（筛选无结果） | "未找到符合条件的回测" + 清除筛选按钮 |
| 详情页（权益曲线） | "权益曲线数据加载中..." / "数据文件缺失" |
| 交易明细（无交易） | "该回测未产生任何交易" |
| 批量对比（未选择） | "请从列表页选择至少 2 个回测进行对比" |
| 参数分析（无结果） | "请先配置参数范围并运行扫描" |

### 7.6 状态持久化

- **筛选条件**：保存到 `localStorage`，刷新后恢复
- **选中项**：不持久化（刷新清空）
- **活跃任务**：保存到 `sessionStorage`，刷新后尝试重连 WebSocket

### 7.7 并发控制

- 同一策略+标的+日期范围的回测，如果已有进行中的任务，禁止重复提交
- 批量回测最多同时运行 5 个

---

## 8. 实现范围与优先级

### 8.1 P0（核心 MVP）

- [ ] FastAPI 后端框架搭建（ROS2 Client Manager、API 路由）
- [ ] React 前端框架搭建（路由、布局、状态管理）
- [ ] 回测列表页（表格、筛选、排序、分页）
- [ ] 回测详情页（权益曲线 Tab、统计指标 Tab）
- [ ] ROS2 Service/Action 集成（执行回测）
- [ ] 增强版 JSON 输出（回测引擎改造）

### 8.2 P1（重要功能）

- [ ] K 线图 + 买卖点标注（TradingView Lightweight Charts）
- [ ] 交易明细 Tab
- [ ] 月度收益热力图
- [ ] 批量对比页
- [ ] WebSocket 实时进度推送
- [ ] 标签管理

### 8.3 P2（增强功能）

- [ ] 参数敏感性分析页
- [ ] 报告导出（PDF/Excel）
- [ ] 拖拽列排序
- [ ] 行内预览卡片

---

*文档结束*
