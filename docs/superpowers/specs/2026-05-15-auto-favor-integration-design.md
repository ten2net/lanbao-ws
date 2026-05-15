# 自选股管理模块集成设计文档

## 背景

`lanbao-auto-favor` 是一个独立的自选股管理工具，通过命令行脚本实现：
- 基于同花顺问财自然语言查询的自动选股
- 东方财富自选股分组同步
- 多账户管理
- 定时选股与清理任务

本设计将其功能完全内迁至揽宝平台，废弃外部脚本，用户通过 Web 端完成全部操作。

## 目标

1. 在揽宝平台内部提供完整的自选股管理功能
2. 数据统一存储到 DuckDB，与现有数据层一致
3. 符合揽宝 ROS2 分布式架构
4. 与 AI 投研、策略系统深度联动

## 非目标

- 多用户隔离（保持单用户模式）
- 替换 stock-select / EastMoney API（保留外部依赖）
- 实时行情推送（使用现有轮询机制）

## 架构设计

```
前端 (React)
  ├── 自选股管理页 (/favor/watchlist)
  ├── 选股条件配置页 (/favor/conditions)
  ├── 选股执行页 (/favor/pick)
  └── 定时任务页 (/favor/schedules)
           │
           │ HTTP /api/v1
           ▼
FastAPI (lanbao_backtest)
  ├── POST /favor/pick
  ├── GET  /favor/watchlist
  ├── POST /favor/watchlist
  ├── DELETE /favor/watchlist/{code}
  ├── GET  /favor/conditions
  ├── POST /favor/conditions
  ├── DELETE /favor/conditions/{id}
  ├── POST /favor/run-schedule/{name}
  └── GET  /favor/pick-logs
           │
           │ ROS2 Service / Action
           ▼
FavorNode (lanbao_favor)
  ├── ConditionManager  ──► DuckDB (favor_conditions)
  ├── StockPicker       ──► stock-select API
  ├── FavorSyncManager  ──► EastMoney API
  └── ScheduleManager   ──► ROS2 Timers
```

## 数据模型

### favor_conditions

| 列名 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | 自增主键 |
| name | VARCHAR | 条件名称 |
| query | VARCHAR | 同花顺问财查询语句 |
| description | VARCHAR | 描述 |
| enabled | BOOLEAN | 是否启用 |
| priority | INTEGER | 优先级（越小越优先） |
| max_results | INTEGER | 最大返回股票数 |
| filter_hot_sector | BOOLEAN | 是否过滤热门板块 |
| filter_min_cap_yi | FLOAT | 最小流通市值（亿元），NULL 表示不过滤 |
| created_at | TIMESTAMP | 创建时间 |
| updated_at | TIMESTAMP | 更新时间 |

### favor_accounts

| 列名 | 类型 | 说明 |
|------|------|------|
| id | VARCHAR PK | 账户标识：default / account2 / wife |
| name | VARCHAR | 显示名称 |
| env_prefix | VARCHAR | 环境变量前缀 |
| target_group | VARCHAR | 默认目标分组 |
| enabled | BOOLEAN | 是否启用 |
| created_at | TIMESTAMP | 创建时间 |

### favor_watchlist

| 列名 | 类型 | 说明 |
|------|------|------|
| code | VARCHAR | 股票代码 |
| name | VARCHAR | 股票名称 |
| account_id | VARCHAR | 所属账户 |
| group_name | VARCHAR | 所属分组 |
| source_condition | VARCHAR | 来源选股条件 |
| signal_type | VARCHAR | 策略信号类型（如 AI_BUY、MA_CROSS） |
| confidence | FLOAT | 置信度 |
| added_at | TIMESTAMP | 添加时间 |
| PRIMARY KEY (code, account_id, group_name) | | |

### favor_pick_logs

| 列名 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | 自增主键 |
| condition_id | INTEGER | 条件 ID |
| condition_name | VARCHAR | 条件名称 |
| picked_count | INTEGER | 选中股票数 |
| filtered_count | INTEGER | 过滤掉的股票数 |
| duration_ms | INTEGER | 执行耗时 |
| picked_codes | VARCHAR[] | 选中的股票代码列表 |
| error_message | VARCHAR | 错误信息 |
| created_at | TIMESTAMP | 创建时间 |

## ROS2 接口设计

### Services

#### /favor/pick

```protobuf
# Request
string[] condition_names    # 指定条件名称列表，空表示所有启用条件
bool clear_existing         # 是否清空现有自选股
string account_id           # 指定账户，空表示所有启用账户

# Response
bool success
string message
int32 total_unique          # 去重后股票总数
int32 added                 # 新增数量
int32 existing              # 已存在数量
string[] codes              # 新增股票代码
```

#### /favor/get_watchlist

```protobuf
# Request
string account_id           # 可选过滤
string group_name           # 可选过滤

# Response
bool success
WatchlistItem[] items

# WatchlistItem
string code
string name
string account_id
string group_name
string source_condition
string signal_type
float64 confidence
string added_at
```

#### /favor/manage_condition

```protobuf
# Request
string operation            # "list" | "get" | "save" | "delete"
int32 id                    # 条件 ID（get/save/delete 时使用）
FavorCondition condition    # save 时使用

# Response
bool success
string message
FavorCondition[] conditions # list 时返回
```

### Actions

#### /favor/run_schedule

```protobuf
# Goal
string schedule_name        # pre_market / morning / afternoon / pre_close / post_market / cleanup_volume / cleanup_hot

# Feedback
string current_step         # 当前执行步骤
float64 progress            # 进度 0.0-1.0
string message              # 状态消息

# Result
bool success
string message
PickResult[] results        # 各条件选股结果
```

### Topics

#### /favor/pick_result (发布)

```protobuf
string condition_name
string[] codes
int32 count
string timestamp
```

AI 投研节点可订阅此 topic，自选股变更时自动触发分析。

## FastAPI 路由设计

| 方法 | 路径 | 功能 | 请求体 | 响应 |
|------|------|------|--------|------|
| POST | `/api/v1/favor/pick` | 执行选股 | `{condition_names?: string[], clear_existing?: boolean, account_id?: string}` | `{success, total_unique, added, existing, codes}` |
| GET | `/api/v1/favor/watchlist` | 获取自选股 | Query: `account_id`, `group_name` | `{items: WatchlistItem[]}` |
| POST | `/api/v1/favor/watchlist` | 手动添加 | `{code, name, account_id?, group_name?, source_condition?}` | `{success}` |
| DELETE | `/api/v1/favor/watchlist/{code}` | 移除 | Query: `account_id`, `group_name` | `{success}` |
| GET | `/api/v1/favor/conditions` | 获取条件 | - | `{conditions: FavorCondition[]}` |
| POST | `/api/v1/favor/conditions` | 保存条件 | `FavorCondition` | `{success, id}` |
| DELETE | `/api/v1/favor/conditions/{id}` | 删除条件 | - | `{success}` |
| POST | `/api/v1/favor/run-schedule/{name}` | 手动触发 | - | `{success, message}` |
| GET | `/api/v1/favor/pick-logs` | 选股日志 | Query: `limit`, `offset`, `condition_id?` | `{logs: PickLog[], total}` |

## 前端页面设计

### 自选股管理页 (/favor/watchlist)

- **分组标签栏**：自选股 / 揽宝 / 短线（可切换）
- **股票表格**：代码、名称、来源条件、信号类型、置信度、添加时间
- **操作**：删除、批量删除、移动分组
- **搜索/过滤**：按代码/名称搜索

### 选股条件配置页 (/favor/conditions)

- **条件卡片列表**：名称、查询语句、描述、启用开关、编辑/删除按钮
- **新增/编辑弹窗**：
  - 名称（输入框）
  - 查询语句（文本域，支持问财语法）
  - 描述（输入框）
  - 启用开关
  - 最大结果数（数字输入）
  - 板块过滤开关
  - 市值过滤（最小流通市值，亿元）
- **临时条件测试区**：输入查询语句，点击测试查看选股结果（不保存）

### 选股执行页 (/favor/pick)

- **执行控制**：
  - 条件选择（多选框，默认全选启用条件）
  - 清空现有选项
  - "开始选股" 按钮
- **执行进度**：步骤指示器 + 实时日志
- **结果展示**：
  - 各条件选股结果（可展开查看股票列表）
  - 去重汇总统计
  - 新增/已存在对比
  - "添加到自选股" 按钮

### 定时任务页 (/favor/schedules)

- **任务表格**：名称、Cron 表达式、下次执行时间、启用开关、手动触发按钮
- **任务详情弹窗**：关联的选股条件、执行历史

## 系统集成点

### 与 AI 投研联动

1. `AIResearchNode` 订阅 `/favor/pick_result` topic，自选股池更新时自动触发个股分析
2. `run_market_daily_research` 默认使用 `favor_watchlist` 中的股票作为分析标的（替代硬编码的沪深300成分股列表）
3. AI 研报中的 BUY 建议可自动同步到自选股"揽宝"分组

### 与策略系统联动

1. 策略节点（如 `lanbao_strategy`）产生 `StockSignal` 消息时，`FavorNode` 监听 `/strategy/signals` topic
2. BUY 信号自动添加到自选股（带 signal_type 和 confidence）
3. SELL 信号可选择自动从自选股移除（可配置）

### 与通知系统联动

`FavorNode` 通过 `LanBaoBaseNode._publish_alert()` 发布系统告警：
- 选股完成：INFO 级别，包含选中股票数
- 清理完成：INFO 级别，包含清理股票数
- 执行失败：ERROR 级别，包含错误信息

告警自动通过现有飞书推送通道发送。

## 组件详细设计

### FavorNode

继承 `LanBaoBaseNode`，实现生命周期方法：

```python
class FavorNode(LanBaoBaseNode):
    def initialize(self) -> bool:
        self._condition_mgr = ConditionManager(self._storage)
        self._picker = StockPicker(self._config)
        self._sync_mgr = FavorSyncManager()
        self._scheduler = ScheduleManager(self)
        self._setup_services()
        self._setup_action_server()
        self._setup_timers()
        return True

    def start(self) -> bool:
        self._scheduler.start()
        return True

    def stop(self):
        self._scheduler.stop()
```

### StockPicker

封装 `stock-select` 客户端，增加过滤逻辑：

```python
class StockPicker:
    def pick(self, condition: FavorCondition) -> List[StockInfo]:
        # 1. 调用 stock-select 执行查询
        result = self._selector.select(condition.query, max_results=condition.max_results)
        stocks = [...]

        # 2. 市值二次过滤
        if condition.filter_min_cap_yi:
            stocks = self._filter_by_market_cap(stocks, condition.filter_min_cap_yi)

        # 3. 板块热度过滤
        if condition.filter_hot_sector:
            stocks = self._filter_by_hot_sectors(stocks)

        return stocks
```

### ScheduleManager

使用 ROS2 Timer 替代 cron：

```python
class ScheduleManager:
    SCHEDULES = {
        "pre_market": {"hour": 9, "minute": 0},
        "morning": {"hour": 10, "minute": 30},
        "afternoon": {"hour": 14, "minute": 0},
        "pre_close": {"hour": 14, "minute": 50},
        "post_market": {"hour": 15, "minute": 30},
        "cleanup_volume": {"hour": 15, "minute": 35},
    }

    def start(self):
        for name, time_spec in self.SCHEDULES.items():
            self._create_daily_timer(name, time_spec)
```

## 错误处理

| 场景 | 处理策略 |
|------|---------|
| stock-select API 不可用 | 记录错误，跳过本次选股，下次定时任务再试 |
| EastMoney API 凭证过期 | 记录 ERROR 告警，通知用户重新登录 |
| 选股结果为空 | 正常完成，记录 0 条结果 |
| DuckDB 写入失败 | 记录 ERROR，重试 3 次后告警 |
| 定时任务重叠（上次未结束） | 跳过本次执行，记录 WARNING |

## 测试策略

1. **单元测试**：
   - `ConditionManager` CRUD 操作
   - `StockPicker` 过滤逻辑（mock stock-select 响应）
   - `ScheduleManager` 定时器触发

2. **集成测试**：
   - FastAPI 端到端路由测试
   - ROS2 Service/Action 调用测试
   - DuckDB 数据持久化测试

3. **前端测试**：
   - 自选股表格 CRUD
   - 选股执行流程
   - 定时任务启停

## 迁移计划

### Phase 1：核心引擎（1-2 天）

- [ ] 创建 `lanbao_favor` ROS2 包（setup.py、package.xml、resource）
- [ ] 实现 DuckDB 表迁移脚本
- [ ] 实现 `FavorNode` 基础框架（initialize/start/stop）
- [ ] 实现 `ConditionManager`（条件 CRUD）
- [ ] 实现 `StockPicker`（选股 + 过滤）
- [ ] 实现 `FavorSyncManager`（EastMoney 同步）
- [ ] 注册到 `scripts/build.sh` 和 `scripts/start_nodes.sh`

### Phase 2：API 与前端（2-3 天）

- [ ] FastAPI 新增 `/favor/*` 路由
- [ ] 前端自选股管理页
- [ ] 前端选股条件配置页
- [ ] 前端选股执行页

### Phase 3：定时任务（1 天）

- [ ] 实现 `ScheduleManager`
- [ ] 配置各时段定时器
- [ ] 实现低成交额/低人气清理逻辑
- [ ] 前端定时任务页

### Phase 4：系统集成（1 天）

- [ ] AI 投研默认使用自选股池
- [ ] 策略信号自动同步到自选股
- [ ] 通知接入系统告警体系

### Phase 5：废弃外部脚本（0.5 天）

- [ ] 确认 `lanbao-auto-favor` 所有功能已迁移
- [ ] 更新文档
- [ ] 归档外部仓库

## 依赖清单

新增依赖：
- `stock-select`（揽宝内部工具，已存在）
- `eastmoney-mcp-server`（揽宝内部工具，已存在）
- `pyyaml`（已存在于 pyproject.toml）

无新增外部依赖。
