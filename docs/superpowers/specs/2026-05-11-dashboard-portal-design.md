# 揽宝回测平台 Dashboard 平台化设计文档

**日期**: 2026-05-11
**主题**: Streamlit Dashboard 功能移植（除回测结果外）到 React 前端
**标准**: 企业级 UI/UX（单用户模式，后端架构不变）
**实现方式**: 一次性完整交付

---

## 1. 需求背景

现有揽宝回测平台前端基于 React + Ant Design，已具备回测列表、回测详情、批量对比、参数分析4个页面。Streamlit Dashboard（`src/lanbao_monitor/dashboard.py`）提供6个页面的实时监控能力，其中回测结果页面与现有前端功能重叠。本次设计将 Streamlit Dashboard 中其余5个页面移植到 React 前端，实现平台化统一入口。

---

## 2. 整体架构

### 2.1 系统架构图

```
┌─────────────────────────────────────────────────────────┐
│                    React 18 + Vite 前端                   │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐       │
│  │主题系统 │ │WebSocket│ │ 导航布局 │ │ 状态管理 │       │
│  │Config   │ │ 管理器   │ │ 组件    │ │ Zustand │       │
│  │Provider │ │         │ │         │ │         │       │
│  └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘       │
│       └─────────────┴──────────┴───────────┘             │
│                         │                               │
│              ┌──────────┴──────────┐                    │
│              │    页面组件层        │                    │
│              │  (5个新页面 + 现有)  │                    │
│              └─────────────────────┘                    │
└─────────────────────────┬───────────────────────────────┘
                          │ WebSocket (ros2 websocket桥)
┌─────────────────────────┴───────────────────────────────┐
│              ROS2 WebSocket Bridge (外部)               │
│         统一转发 ROS2 Topics → WebSocket 客户端          │
└─────────────────────────┬───────────────────────────────┘
                          │ ROS2 Topics
┌─────────────────────────┴───────────────────────────────┐
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐ │
│  │ 系统指标节点 │  │ 监控节点    │  │   回测/数据节点  │ │
│  │(CPU/内存/   │  │(节点状态/   │  │                 │ │
│  │ 磁盘→Topic) │  │  告警→Topic)│  │                 │ │
│  └─────────────┘  └─────────────┘  └─────────────────┘ │
│                      ROS2 网络                          │
└─────────────────────────────────────────────────────────┘
```

### 2.2 技术栈确认

| 层级 | 技术 | 说明 |
|------|------|------|
| 前端框架 | React 18 + TypeScript + Vite 5 | 复用现有技术栈 |
| UI 组件库 | Ant Design 5 | 复用现有组件库 |
| 图表 | Recharts + lightweight-charts | 复用现有图表库 |
| 状态管理 | Zustand 4 | 扩展现有 store |
| 数据获取 | TanStack Query v5 + Axios | HTTP API 调用 |
| 实时数据 | WebSocket (ros2 websocket 桥) | 统一 ROS2 Topic 订阅 |
| 主题 | Ant Design ConfigProvider + CSS Variables | 自适应 light/dark |

---

## 3. 前端架构升级

### 3.1 主题系统

- **实现**: Ant Design 5 `ConfigProvider` + 自定义 CSS Variables
- **配色方案**:
  - 品牌色: `#1677ff`
  - 成功: `#52c41a`
  - 警告: `#faad14`
  - 危险: `#f5222d`
- **切换逻辑**:
  - 默认跟随系统 `prefers-color-scheme`
  - 提供手动切换开关（顶部导航栏）
  - 用户选择持久化到 `localStorage`
- **图表适配**: Recharts / lightweight-charts 根据当前主题切换配色（坐标轴颜色、网格线、系列颜色）

### 3.2 WebSocket 连接管理器

**文件位置**: `web/src/services/ros2WebSocket.ts`

**职责**:
- 封装 ros2 websocket 桥的连接生命周期
- 自动重连（指数退避，初始1秒，最大30秒）
- Topic 订阅/取消订阅管理
- 连接状态暴露给全局状态

**接口设计**:

```typescript
interface ROS2BridgeMessage {
  op: 'subscribe' | 'unsubscribe' | 'publish';
  topic: string;
  type?: string;
  msg?: unknown;
}

interface ROS2BridgeEvent {
  topic: string;
  msg: unknown;
  timestamp: number;
}

class ROS2WebSocketManager {
  connect(url: string): void;
  disconnect(): void;
  subscribe(topic: string, callback: (msg: unknown) => void): void;
  unsubscribe(topic: string, callback: (msg: unknown) => void): void;
  getConnectionState(): 'connecting' | 'connected' | 'disconnected' | 'reconnecting';
}
```

**React Hook**:

```typescript
// hooks/useROSTopic.ts
function useROSTopic<T>(topic: string, onMessage: (msg: T) => void): void;
```

**连接状态可视化**: 顶部导航栏右侧显示状态指示灯
- 绿色: 已连接
- 黄色: 重连中
- 红色: 离线

### 3.3 双层导航布局

**文件位置**: `web/src/components/AppShell/`

```
┌────────────────────────────────────────┐
│  [Logo]  投研中心  实时监控  数据管理  系统设置 │  ← 顶部一级导航
├────────┬───────────────────────────────┤
│ 侧边栏  │                               │
│ 二级页  │      页面内容区域              │
│ 面列表  │      (可滚动)                 │
│        │                               │
└────────┴───────────────────────────────┘
```

**一级导航（顶部）**:
| 模块 | 包含页面 |
|------|----------|
| 投研中心 | 回测列表、批量对比、参数分析 |
| 实时监控 | 系统概览、节点状态、风险监控 |
| 数据管理 | 数据底座 |
| 系统设置 | 系统配置 |

**二级导航（侧边）**: 根据当前一级导航动态渲染，默认选中第一个页面。

**响应式行为**:
- 桌面端（≥1280px）: 顶部 + 侧边完整展示
- 平板端（768px-1279px）: 侧边栏可收起为图标模式
- 移动端（<768px）: 侧边栏变为抽屉（Drawer）

### 3.4 状态管理层扩展

| Store | 职责 | 持久化 |
|-------|------|--------|
| `themeStore` | 主题模式（light/dark/auto）、手动切换状态 | localStorage |
| `wsStore` | WebSocket 连接状态、已订阅 Topic 列表、最近消息缓存 | 无 |
| `monitorStore` | 节点列表、告警列表、系统指标时序数据（最近30分钟） | 无 |
| `dataStore` | 数据同步状态、数据表列表、数据质量报告 | 无 |
| `configStore` | 系统配置表单状态、保存状态 | 无 |

---

## 4. 页面详细设计

### 4.1 系统概览（实时监控 → 系统概览）

**用途**: 平台健康状态的一屏总览，运维人员默认落地页。

**布局**: 顶部 KPI 行 + 2×2 网格卡片。

**KPI 行（4个指标）**:
| 指标 | 数据来源 | 刷新频率 |
|------|----------|----------|
| 在线节点数 | `/node/status` | WebSocket 推送 |
| 今日告警数 | `/risk/alerts` | WebSocket 推送 |
| CPU 使用率 | `/system/metrics` | WebSocket 推送（5秒周期） |
| 内存使用率 | `/system/metrics` | WebSocket 推送（5秒周期） |

**图表卡片**:
| 位置 | 内容 | 交互 |
|------|------|------|
| 左上 | CPU 使用率时序折线图（最近30分钟） | 悬停显示数值，时间范围可切换 |
| 右上 | 内存使用率时序折线图（最近30分钟） | 同上 |
| 左下 | 节点状态分布饼图（在线/离线/警告/错误） | 点击扇形可筛选节点列表 |
| 右下 | 最近告警滚动列表（Top 5，带级别颜色标识） | 点击跳转风险监控页 |

**空状态**: 无节点时显示「暂无节点数据」占位图。

### 4.2 节点状态（实时监控 → 节点状态）

**用途**: ROS2 节点级别的详细监控与运维。

**布局**: 左右分栏（3:7）。

**左侧面板 — 节点列表**:
- 节点卡片列表，每卡片显示：节点名称、状态指示灯、CPU/内存占用、最后心跳时间
- 支持按状态筛选（全部/在线/离线/警告/错误）
- 支持按名称搜索
- 点击卡片选中，右侧展示详情

**右侧面板 — 节点详情**:
- 节点基本信息：名称、状态、启动时间、运行时长
- QoS 配置表格（话题名、QoS 策略）
- 订阅/发布话题列表
- 指标趋势图（CPU/内存，最近1小时）
- 操作区：「重启节点」按钮（调用 ROS2 Service）

**数据来源**: `/node/status`、`/node/metrics`（WebSocket）

### 4.3 风险监控（实时监控 → 风险监控）

**用途**: 实时风险告警中心，支持告警确认与历史追溯。

**布局**: 顶部统计栏 + 中部告警表格 + 底部告警趋势图。

**统计栏（4个指标）**:
| 指标 | 计算方式 |
|------|----------|
| 今日告警总数 | 今日 00:00 至今的 `/risk/alerts` 消息计数 |
| 严重告警数 | 级别为 `critical` 的告警计数 |
| 警告告警数 | 级别为 `warning` 的告警计数 |
| 已处理数 | 状态为 `acknowledged` 的告警计数 |

**告警表格**:
| 列 | 说明 |
|----|------|
| 时间 | 告警触发时间，精确到秒 |
| 级别 | critical / warning / info，带颜色标签 |
| 类型 | 风险类型（如「回撤超限」「仓位过高」） |
| 描述 | 告警详细描述 |
| 关联 | 关联策略/节点名称 |
| 操作 | 「确认」/「忽略」按钮 |

**表格功能**: 按级别/类型/时间范围筛选、分页（默认20条/页）、排序（时间倒序）。

**告警趋势图**: 24小时堆叠面积图，按告警级别分组，X轴为小时，Y轴为告警数量。

**实时通知**: 新告警到达时，页面右上角显示 Ant Design `notification`，持续5秒。

**数据来源**: `/risk/alerts`（WebSocket）

### 4.4 数据底座（数据管理 → 数据底座）

**用途**: DuckDB 数据资产的概览、质量监控与同步管理。

**布局**: 顶部统计卡片 + 中部数据表列表 + 底部两栏（同步状态 + 数据质量）。

**统计卡片（4个）**:
| 指标 | 数据来源 |
|------|----------|
| 总股票数 | `SELECT COUNT(DISTINCT symbol) FROM stock_info` |
| 日线数据条数 | `SELECT COUNT(*) FROM stock_daily` |
| 最后同步时间 | `sync_status` 表 |
| 数据覆盖天数 | `stock_daily` 的日期范围 |

**数据表列表**:
| 列 | 说明 |
|----|------|
| 表名 | 如 `stock_daily`、`stock_info` |
| 记录数 | 格式化显示（如 1.2M） |
| 数据起止日期 | 该表的数据时间范围 |
| 最新更新时间 | 最后写入时间 |
| 数据质量评分 | 0-100，带颜色标识（≥90绿，70-90黄，<70红） |
| 操作 | 「预览」按钮（弹出 Drawer 显示前100行） |

**同步状态区**:
- 同步任务列表：数据源、状态（运行中/成功/失败）、进度条、成功/失败计数、耗时
- 「手动同步」按钮：触发增量同步任务

**数据质量区**:
- 缺失数据热力图：X轴为最近30天，Y轴为股票代码（采样前50支），颜色深浅标识缺失程度
- 数据质量趋势折线图（最近7天）

**数据来源**: HTTP API（`/api/v1/data/*`）

### 4.5 系统配置（系统设置 → 系统配置）

**用途**: 平台运行参数的统一配置管理。

**布局**: 分组表单，左侧固定分组锚点导航，右侧表单区域。

**配置分组**:

| 分组 | 字段 | 组件 | 默认值 | 验证规则 |
|------|------|------|--------|----------|
| **回测参数** | 默认初始资金 | InputNumber | 1,000,000 | > 0 |
| | 默认佣金率 | InputNumber | 0.0003 | 0-0.01 |
| | 默认滑点 | InputNumber | 0.001 | 0-0.05 |
| | 默认回测区间 | RangePicker | 最近1年 | 起止日期有效 |
| **风险控制** | 最大单笔亏损比例 | InputNumber | 0.05 | 0-1 |
| | 最大回撤阈值 | InputNumber | 0.15 | 0-1 |
| | 仓位上限 | InputNumber | 0.8 | 0-1 |
| | 熔断开关 | Switch | false | - |
| **数据同步** | 自动同步开关 | Switch | true | - |
| | 同步时间 | TimePicker | 09:00 | - |
| | 数据源优先级 | Select | Tushare > TDX > AKShare > MiniQMT | - |
| **通知设置** | Webhook URL | Input | "" | URL 格式 |
| | 告警级别阈值 | Select | warning | - |

**交互**:
- 表单底部固定操作栏：「保存配置」「重置为默认值」
- 关键配置（如熔断开关、仓位上限）变更时弹出确认弹窗
- 保存成功显示 `message.success()`，失败显示错误原因
- 页面加载时显示 Skeleton 占位

**数据来源**: HTTP API（`/api/v1/config` GET/PUT）

---

## 5. 后端配合改动

### 5.1 新增 ROS2 节点：system_metrics_node

**位置**: `src/lanbao_monitor/lanbao_monitor/system_metrics_node.py`

**功能**:
- 继承 `LanBaoBaseNode`
- 周期（5秒）采集系统指标（psutil）
- 发布到 `/system/metrics`

**新增消息类型**（`src/lanbao_interfaces/msg/SystemMetrics.msg`）:
```rosidl
builtin_interfaces/Time timestamp
float32 cpu_percent
float32 memory_percent
float32 disk_percent
uint64 network_bytes_sent
uint64 network_bytes_recv
float32 load_average_1m
```

### 5.2 FastAPI 新增接口

| 接口 | 方法 | 请求/响应 | 说明 |
|------|------|-----------|------|
| `/api/v1/data/summary` | GET | `{} → DataSummary` | 数据概览统计 |
| `/api/v1/data/tables` | GET | `{} → DataTable[]` | 数据表列表 |
| `/api/v1/data/sync` | GET | `{} → SyncTask[]` | 同步状态 |
| `/api/v1/data/sync` | POST | `{source?: string} → SyncTask` | 手动触发同步 |
| `/api/v1/data/quality` | GET | `{?table, ?start_date, ?end_date} → QualityReport` | 数据质量报告 |
| `/api/v1/config` | GET | `{} → SystemConfig` | 读取配置 |
| `/api/v1/config` | PUT | `SystemConfig → SystemConfig` | 更新配置 |

### 5.3 配置持久化

系统配置保存为 YAML 文件（`config/lanbao.yaml` 或 `config/settings.yaml`），后端启动时加载，修改时热更新。

---

## 6. 数据流详细设计

### 6.1 WebSocket 通信协议

**连接 URL**: `ws://<ros2-websocket-bridge>:9090`

**订阅消息**:
```json
{
  "op": "subscribe",
  "topic": "/system/metrics",
  "type": "lanbao_interfaces/msg/SystemMetrics"
}
```

**取消订阅**:
```json
{
  "op": "unsubscribe",
  "topic": "/system/metrics"
}
```

**接收消息**:
```json
{
  "topic": "/system/metrics",
  "msg": {
    "timestamp": { "sec": 1715431200, "nanosec": 0 },
    "cpu_percent": 35.5,
    "memory_percent": 62.3,
    "disk_percent": 78.0,
    "network_bytes_sent": 123456789,
    "network_bytes_recv": 987654321,
    "load_average_1m": 1.23
  }
}
```

### 6.2 前端 Topic 订阅矩阵

| 页面 | 订阅 Topic | 用途 |
|------|-----------|------|
| 系统概览 | `/system/metrics` | CPU/内存实时指标 |
| 系统概览 | `/node/status` | 节点状态分布 |
| 系统概览 | `/risk/alerts` | 最近告警 |
| 节点状态 | `/node/status` | 节点列表与详情 |
| 节点状态 | `/node/metrics` | 节点级指标趋势 |
| 风险监控 | `/risk/alerts` | 告警列表与统计 |
| 数据底座 | （HTTP API） | 数据概览/表/同步/质量 |
| 系统配置 | （HTTP API） | 配置读写 |

### 6.3 时序数据前端缓存策略

监控类时序数据（CPU、内存、告警）在前端 `monitorStore` 中维护固定长度队列（最近30分钟/100条），超出时丢弃旧数据，保证内存不泄漏。

---

## 7. 错误处理

| 场景 | 处理策略 | 用户感知 |
|------|----------|----------|
| WebSocket 断线 | 自动重连（指数退避，最大30秒） | 顶部指示灯变黄→红，全局提示「实时数据连接中断」 |
| ros2 websocket 桥不可用 | 停止重连，显示离线状态 | 页面降级显示缓存数据，提示检查桥服务 |
| Topic 消息格式异常 | 忽略该条，console.warn | 无感知，不影响其他数据 |
| HTTP API 失败 | 显示 `message.error()`，提供重试 | 明确错误提示（如「获取数据失败，请重试」） |
| 节点离线 | 节点卡片状态变红 | 详情页显示「节点已离线」占位 |
| 配置保存失败 | 表单保持编辑状态，显示字段级错误 | 明确提示失败原因 |

---

## 8. 测试策略

| 测试类型 | 范围 | 工具 |
|----------|------|------|
| 单元测试 | WebSocket 管理器、主题切换 Hook、各页面纯组件 | Vitest + React Testing Library |
| 集成测试 | 页面 + MSW 模拟 API + Mock WebSocket 服务器 | Vitest + MSW + mock-socket |
| E2E 测试 | 关键用户流程 | Playwright |
| 视觉回归 | 5个新页面 light/dark 主题截图对比 | Playwright + pixelmatch |

**E2E 核心流程**:
1. 打开系统概览页 → 验证 KPI 卡片渲染
2. 切换暗黑模式 → 验证图表配色变化
3. 进入节点状态页 → 验证节点列表渲染
4. 点击节点卡片 → 验证详情面板更新
5. 进入系统配置页 → 修改配置 → 保存 → 验证成功提示

---

## 9. 目录结构

```
web/src/
├── App.tsx                          # 路由配置（扩展双层导航）
├── main.tsx
├── services/
│   ├── ros2WebSocket.ts             # [新增] WebSocket 管理器
│   └── config.ts                    # [新增] 配置 API
├── hooks/
│   ├── useROSTopic.ts               # [新增] ROS2 Topic 订阅 Hook
│   ├── useSystemMetrics.ts          # [新增] 系统指标 Hook
│   ├── useNodeStatus.ts             # [新增] 节点状态 Hook
│   └── useAlerts.ts                 # [新增] 告警 Hook
├── components/
│   ├── AppShell/                    # [新增] 双层导航布局
│   │   ├── AppShell.tsx
│   │   ├── TopNav.tsx               # 顶部一级导航
│   │   ├── SideNav.tsx              # 侧边二级导航
│   │   └── ConnectionStatus.tsx     # WebSocket 状态指示灯
│   ├── ThemeToggle/                 # [新增] 主题切换按钮
│   └── Monitor/                     # [新增] 监控通用组件
│       ├── KPIGrid.tsx              # KPI 指标卡片网格
│       ├── MetricChart.tsx          # 指标时序图（封装 Recharts）
│       ├── StatusPieChart.tsx       # 状态分布饼图
│       └── AlertBadge.tsx           # 告警级别徽章
├── pages/
│   ├── BacktestListPage.tsx         # [已有]
│   ├── BacktestDetailPage.tsx       # [已有]
│   ├── ComparePage.tsx              # [已有]
│   ├── ParamAnalysisPage.tsx        # [已有]
│   ├── SystemOverviewPage.tsx       # [新增] 系统概览
│   ├── NodeStatusPage.tsx           # [新增] 节点状态
│   ├── RiskMonitorPage.tsx          # [新增] 风险监控
│   ├── DataCenterPage.tsx           # [新增] 数据底座
│   └── SystemConfigPage.tsx         # [新增] 系统配置
├── stores/
│   ├── backtestStore.ts             # [已有]
│   ├── themeStore.ts                # [新增] 主题状态
│   ├── wsStore.ts                   # [新增] WebSocket 状态
│   ├── monitorStore.ts              # [新增] 监控数据状态
│   ├── dataStore.ts                 # [新增] 数据底座状态
│   └── configStore.ts               # [新增] 配置状态
├── types/
│   ├── backtest.ts                  # [已有]
│   ├── ros2.ts                      # [新增] ROS2 相关类型
│   ├── monitor.ts                   # [新增] 监控类型
│   ├── data.ts                      # [新增] 数据底座类型
│   └── config.ts                    # [新增] 配置类型
└── api/
    ├── client.ts                    # [已有]
    ├── backtest.ts                  # [已有]
    ├── strategy.ts                  # [已有]
    └── data.ts                      # [新增] 数据底座 API
```

---

## 10. 依赖清单

**无需新增运行时依赖**。现有技术栈已覆盖：
- Ant Design 5（主题、组件）
- Zustand（状态管理）
- Recharts（图表）
- TanStack Query（HTTP 数据获取）

**开发依赖新增**:
- `mock-socket`（WebSocket 集成测试模拟）
- `@testing-library/react-hooks`（Hook 单元测试）

---

## 11. 风险与注意事项

1. **ros2 websocket 桥依赖**: 实时监控功能依赖外部 ros2 websocket 桥服务，需在部署文档中明确该依赖。
2. **时序数据内存管理**: 前端长期运行可能积累大量时序数据，必须实现固定长度队列，防止内存泄漏。
3. **主题切换闪烁**: Ant Design ConfigProvider 切换主题时可能有短暂闪烁，建议用 CSS transition 平滑过渡。
4. **移动端适配**: 监控仪表盘信息密度高，移动端体验可能受限，优先保证桌面端体验。
5. **现有页面兼容性**: 升级导航布局时需确保现有回测页面不受影响。
