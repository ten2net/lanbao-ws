# Tushare 财务三大报表同步功能设计文档

## 背景

数据同步节点（`DataSyncNode`）目前仅同步 A 股日线行情数据，缺少财务数据（资产负债表、利润表、现金流量表）的同步能力。AI 研究 Agent（基本面分析师、投资组合总监）需要财务数据来做深度分析。

## 目标

为 `DataSyncNode` 新增 Tushare 财务三大报表的定期全量同步功能：
- 同步范围：全市场 A 股，从 2020 年开始
- 同步频率：每周日凌晨自动执行 + 手动触发
- 数据完整性：同步完整字段（核心字段单独列 + `raw_json` 存完整数据）
- 速率限制：遵守 Tushare 80次/分钟 限制
- 存储：复用现有 `DuckDBStorage`

## 架构设计

在现有 `DataSyncNode` 内新增一条独立的**财务数据同步流水线**，与日线同步共享节点基础设施但逻辑完全隔离。

```
┌─────────────────────────────────────────────────────────────┐
│                    DataSyncNode                              │
│  ┌──────────────────┐    ┌──────────────────────────────┐  │
│  │ 日线同步流水线    │    │ 财务数据同步流水线            │  │
│  │ (现有)            │    │ (新增)                        │  │
│  │ _sync_job()      │    │ _sync_financial_job()         │  │
│  └────────┬─────────┘    └──────────────┬───────────────┘  │
│           │                              │                  │
│           └──────────────┬───────────────┘                  │
│                          ▼                                  │
│              ┌─────────────────────┐                        │
│              │   TushareAdapter     │                        │
│              │  (共享 80次/min)     │                        │
│              └──────────┬──────────┘                        │
│                         ▼                                   │
│              ┌─────────────────────┐                        │
│              │   DuckDBStorage      │                        │
│              │  (文件锁互斥访问)     │                        │
│              └─────────────────────┘                        │
└─────────────────────────────────────────────────────────────┘
```

## 组件变更

| 组件 | 变更内容 |
|------|----------|
| `TushareAdapter` | 新增 `get_balance_sheet(ts_code, period)`、`get_income_statement(ts_code, period)`、`get_cashflow_statement(ts_code, period)`；财务接口使用独立限流（0.75s/次） |
| `DuckDBStorage` | 新增 `balance_sheet`、`income_statement`、`cashflow_statement` 三张表；新增 6 个存取方法；`_init_tables()` 中创建新表 |
| `DataSyncNode` | 新增配置加载、`_sync_financial_job()`、`_build_financial_sync_tasks()`、独立定时器、Service、Topic 触发器 |
| `config/lanbao.yaml` | 新增 `financial_sync` 配置块 |

## 数据流

```
1. 触发（定时 / Service / Topic）
        │
        ▼
2. DataSyncNode._sync_financial_job()
   ├── 获取全市场 A 股列表（复用现有 stock_list）
   ├── 查询数据库已有财务数据的最新报告期
   ├── 构建同步任务：缺失报告期的 (股票, 报表类型, 报告期) 组合
   │
   ├── 申请数据库写入锁（复用现有锁机制）
   │
   ├── 循环调用 TushareAdapter：
   │     ├─ get_balance_sheet(ts_code, period)      → 0.75s 间隔
   │     ├─ get_income_statement(ts_code, period)   → 共享配额
   │     └─ get_cashflow_statement(ts_code, period) → 共享配额
   │
   └── 写入 DuckDB → 更新同步状态 → 释放锁
```

## 表结构设计

### balance_sheet（资产负债表）

```sql
CREATE TABLE IF NOT EXISTS balance_sheet (
    symbol VARCHAR NOT NULL,
    report_period VARCHAR NOT NULL,  -- 报告期, e.g. '20241231'
    ann_date VARCHAR,                -- 公告日期
    total_assets DOUBLE,
    total_liab DOUBLE,
    total_hldr_eqy_exc_min_int DOUBLE,
    raw_json VARCHAR,                -- Tushare 返回的完整字段 JSON
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (symbol, report_period)
);
```

### income_statement（利润表）

```sql
CREATE TABLE IF NOT EXISTS income_statement (
    symbol VARCHAR NOT NULL,
    report_period VARCHAR NOT NULL,
    ann_date VARCHAR,
    revenue DOUBLE,
    operate_profit DOUBLE,
    net_income DOUBLE,
    raw_json VARCHAR,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (symbol, report_period)
);
```

### cashflow_statement（现金流量表）

```sql
CREATE TABLE IF NOT EXISTS cashflow_statement (
    symbol VARCHAR NOT NULL,
    report_period VARCHAR NOT NULL,
    ann_date VARCHAR,
    net_operate_cash_flow DOUBLE,
    net_invest_cash_flow DOUBLE,
    net_finance_cash_flow DOUBLE,
    raw_json VARCHAR,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (symbol, report_period)
);
```

**设计要点：**
- `report_period` 格式为 `YYYYMMDD`（如 `20241231`），与 Tushare 财务接口标准参数一致
- 核心财务指标单独成列（便于 SQL 查询），完整原始数据以 JSON 存入 `raw_json`
- 三张表结构对称，便于统一处理

## DuckDBStorage 新增方法

```python
class DuckDBStorage:
    def save_balance_sheet(self, symbol: str, period: str, data: pd.DataFrame) -> bool
    def get_balance_sheet(self, symbol: str, period: Optional[str] = None) -> pd.DataFrame
    def save_income_statement(self, symbol: str, period: str, data: pd.DataFrame) -> bool
    def get_income_statement(self, symbol: str, period: Optional[str] = None) -> pd.DataFrame
    def save_cashflow_statement(self, symbol: str, period: str, data: pd.DataFrame) -> bool
    def get_cashflow_statement(self, symbol: str, period: Optional[str] = None) -> pd.DataFrame
    def get_existing_financial_periods(self) -> Dict[str, Set[str]]
```

## 速率限制策略

现有 `TushareAdapter` 使用 `_min_interval = 0.1s`（10 QPS），仅满足日线接口。升级为**全局双模式限流**：

```python
class TushareAdapter:
    def __init__(self, ...):
        self._min_interval = 0.1          # 日线接口：10 QPS
        self._financial_interval = 0.75   # 财务接口：80次/min ≈ 0.75s/次
        self._last_financial_request = 0  # 财务接口独立计时

    def _rate_limit(self, financial=False):
        """统一速率限制，financial=True 时使用更严格的限流"""
        interval = self._financial_interval if financial else self._min_interval
        last = self._last_financial_request if financial else self._last_request_time
        elapsed = time.time() - last
        if elapsed < interval:
            time.sleep(interval - elapsed)
        if financial:
            self._last_financial_request = time.time()
        else:
            self._last_request_time = time.time()
```

**关键行为：** 日线同步和财务同步共享同一个 `TushareAdapter` 实例时，财务接口的 0.75s 间隔会自动让日线同步也变慢——这是预期行为，避免触发 Tushare 封禁。

## 错误处理

| 场景 | 处理策略 |
|------|----------|
| 单只股票某张报表获取失败 | 记录日志，标记为失败，继续下一只，**不中断整体同步** |
| Tushare API 返回速率超限（429） | 指数退避重试：等待 5s → 10s → 20s，最多 3 次 |
| Tushare API 临时不可用 | 暂停同步，发送 ERROR alert，标记状态为 `failed` |
| 数据库写入锁获取失败 | 等待 60 秒后重试（复用现有逻辑），仍失败则终止 |
| 网络超时 | 重试 2 次，仍失败则标记该任务失败 |

## 触发机制

| 方式 | 实现 | 用途 |
|------|------|------|
| **定时自动** | 独立定时器 `_financial_schedule_timer`，可配置 `financial_sync_day` 和 `financial_sync_time` | 低频率自动同步（每周日凌晨） |
| **ROS2 Service** | 新增 Service `/data_sync/trigger_financial_sync` | 外部系统/API 主动触发 |
| **ROS2 Topic** | 新增订阅 `/data/trigger_financial_sync` | 手动触发、调试 |
| **启动时** | `financial_run_on_startup` 配置 | 开发测试用 |

与日线同步完全独立：财务同步有自己的 `_financial_sync_running` 标志和后台线程，两者可并发执行（但共享 Tushare API 配额）。

## 同步任务构建

```python
def _build_financial_sync_tasks(self, stock_list: pd.DataFrame) -> List[Dict]:
    """
    构建财务同步任务。
    财务数据是季度数据，报告期为每年 3/6/9/12 月的最后一天。
    """
    # 生成从 2020 年至今的所有报告期
    periods = self._generate_report_periods('20200101')

    # 查询数据库已有数据
    existing = read_storage.get_existing_financial_periods()

    tasks = []
    for _, row in stock_list.iterrows():
        symbol = row['symbol']
        missing_periods = [p for p in periods if p not in existing.get(symbol, set())]
        for period in missing_periods:
            # 每个任务包含一只股票在一个报告期的三张报表
            tasks.append({
                'symbol': symbol,
                'period': period,
                'reports': ['balance_sheet', 'income_statement', 'cashflow_statement']
            })
    return tasks
```

**报告期生成规则：** 从 2020Q1（`20200331`）到当前日期前一完整季度，每年 4 个报告期：0331、0630、0930、1231。

## 配置项

```yaml
data_sync:
  # 现有日线同步配置...
  schedule_time: '17:00'

  # 新增财务同步配置
  financial_sync:
    enabled: true
    sync_day: 'sun'           # 周日执行（mon/tue/wed/thu/fri/sat/sun）
    sync_time: '02:00'        # 凌晨 2 点
    start_period: '20200101'  # 最早报告期
    run_on_startup: false
    batch_report_interval: 100  # 每 100 只股票报告进度
```

## 进度报告

每同步 100 只股票（300 次请求）报告一次进度：

```
财务同步进度: 300/5000 只股票, 成功 290, 失败 10, 预计剩余 65 分钟
```

## 测试策略

| 测试类型 | 内容 |
|----------|------|
| **单元测试** | `TushareAdapter.get_balance_sheet()` 等 3 个新方法的 mock 测试（mock `ts.pro_api` 返回） |
| **单元测试** | `DuckDBStorage.save_balance_sheet()` / `get_balance_sheet()` 的 CRUD 测试 |
| **单元测试** | `_build_financial_sync_tasks()` 的报告期生成和缺失检测逻辑 |
| **集成测试** | 端到端：触发同步 → 拉取 Tushare 真实数据（限制 1-2 只股票）→ 写入 DuckDB → 查询验证 |
| **限流测试** | 验证 80次/分钟 限流下，连续请求不触发 Tushare 限速错误 |

### 关键测试场景

```python
def test_build_financial_tasks():
    # 模拟数据库已有 000001.SZ 的 2024Q1-Q3 数据
    # 当前日期 2025-05-14，应生成 2024Q4 任务
    tasks = node._build_financial_sync_tasks(stock_list)
    assert any(t['symbol'] == '000001.SZ' and t['period'] == '20241231' for t in tasks)
```

## 变更清单

| 文件 | 变更类型 | 说明 |
|------|----------|------|
| `src/lanbao_data/lanbao_data/tushare_adapter.py` | 修改 | 新增 3 个财务接口 + 财务限流 |
| `src/lanbao_data/lanbao_data/duckdb_storage.py` | 修改 | 新增 3 张表 + 6 个存取方法 |
| `src/lanbao_data/lanbao_data/data_sync_node.py` | 修改 | 新增财务同步任务、触发器、配置、进度报告 |
| `config/lanbao.yaml` | 修改 | 新增 `financial_sync` 配置块 |
| `tests/test_data_sync/` | 新增 | 单元测试和集成测试 |

## 非目标（明确排除）

- **财务报表指标计算**：仅同步原始报表数据，不做 ROE、PE 等指标计算（留给上层 Agent）
- **实时财务数据更新**：财务数据按季度发布，不做日内实时更新
- **多数据源 fallback**：财务数据仅使用 Tushare，不接入 AKShare 等备用源（Tushare 财务数据完整性和准确性最高）
- **前端展示页面**：本次仅做数据同步层，前端展示在后续迭代中考虑
