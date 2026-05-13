# 揽宝智能投研模块设计文档

## 概述

在揽宝 ROS2 分布式架构中引入多智能体 LLM 投研分析能力。参考 TradingAgents 的多角色协作思想，在揽宝现有技术栈内实现独立投研分析模块（第一阶段），为后续策略信号集成（第二阶段）奠定基础。

## 设计决策

- **架构方案**：方案 2（单节点多智能体引擎），在揽宝 ROS2 框架内新建 `ai_research_node`
- **实现方式**：C 方案 — 参考 TradingAgents 架构思想，在揽宝 ROS2 框架内全新实现
- **数据访问**：全部通过 ROS2 Service 调用现有数据节点，智能体节点不直接访问 DuckDB/数据源
- **前端集成**：直接集成到现有 React + Vite + Ant Design Portal
- **LLM 优先**：国产大模型（DeepSeek 等）
- **新闻源**：中文财经源（东方财富快讯等）

## 智能体架构

### 精简后的 5 个智能体

| # | 智能体 | 职责 | 分析输入 |
|---|--------|------|----------|
| 1 | **宏观分析师** (MacroAnalyst) | 大盘走势、板块轮动、政策环境 | 指数 OHLCV、板块涨跌 |
| 2 | **基本面分析师** (FundamentalAnalyst) | 财务健康度、估值合理性、行业地位 | 财务三表、估值指标 |
| 3 | **技术分析师** (TechnicalAnalyst) | K 线形态、技术指标、支撑/压力位 | 历史 OHLCV + 技术指标 |
| 4 | **情绪新闻分析师** (SentimentNewsAnalyst) | 市场情绪、资金流向、新闻解读 | 资金流向、财经新闻 |
| 5 | **投资总监** (PortfolioDirector) | 综合四方报告，Bull/Bear 辩论，最终评级 | 以上全部报告 |

### 协作流程

**阶段 1 — 并行分析**（所有智能体同时启动）：
- 宏观分析师分析大盘环境
- 基本面分析师批量分析个股（每只股票独立 LLM 调用，可并发）
- 技术分析师批量分析个股
- 情绪新闻分析师批量分析个股

**阶段 2 — 串行综合**（阶段 1 全部完成后）：
- 投资总监汇总所有报告，进行内部 Bull/Bear 辩论
- 输出综合评级、推荐理由、风险提示、仓位建议

### 时间预算

以 10 只关注标的为例，阶段 1 并行约 15-20 分钟，阶段 2 串行约 15-20 分钟，总计 30-40 分钟，控制在 1 小时内。

## 系统组件

### ROS2 接口定义

**新增 Action：`RunResearch`**
```idl
# Goal
string research_type        # "market_daily" | "stock_analysis"
string[] symbols
string report_id

---
# Result
bool success
string report_id
string report_path
string error_message

---
# Feedback
string current_agent
string status
float32 progress
string message
```

**新增 Service：`GetResearchReport`**
```idl
# Request
string report_id

---
# Response
bool found
string report_json
string created_at
```

**新增 Topic：`/research/reports`**
```idl
string report_id
string report_type
string[] symbols
string summary
string verdict
float32 confidence
string created_at
```

### 数据服务扩展

`data_sync_node` 需新增以下服务：

| 服务名 | 用途 | 优先级 |
|--------|------|--------|
| `GetFinancialData` | 获取财务数据 | 高 |
| `GetCapitalFlow` | 获取资金流向 | 中 |
| `SaveResearchReport` | 保存报告元数据 | 高 |
| `GetResearchReports` | 查询历史报告 | 高 |

### 核心类设计

**`AgentOrchestrator`** — 异步调度中心，管理阶段 1 并行 + 阶段 2 串行

**`BaseAgent`** — 智能体基类，定义 `analyze()` 抽象方法，封装 `_call_llm()`

**`LLMClient`** — 统一 LLM 接口，支持多 Provider、自动重试、流式响应、Token 统计

**`ROS2DataClient`** — 统一 ROS2 数据服务客户端，封装对现有数据节点的 Service 调用

### 后端 API

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/api/v1/research/market-daily` | 触发市场日报 |
| `GET` | `/api/v1/research/status/{report_id}` | 查询进度 |
| `GET` | `/api/v1/research/report/{report_id}` | 获取报告 |
| `POST` | `/api/v1/research/stock` | 触发个股分析 |
| `GET` | `/api/v1/research/reports` | 历史列表 |

API 层通过 ROS2 Action Client 调用 `ai_research_node`，与现有回测 API 模式一致。

## 数据流

```
[定时触发] → data_sync_node 同步完成
                → ROS2 Topic /data_sync/completed
                    → ai_research_node 启动分析
                        → 并行调用 4 个智能体
                            → 每个智能体通过 ROS2 Service 获取数据
                        → 投资总监综合
                        → SaveResearchReport 写入 DuckDB 元数据
                        → 写入 Markdown 文件
                        → Publish /research/reports
                            → Portal 前端展示
```

## 报告格式

**结构化 JSON**（DuckDB + API）：包含 `summary`、`macro_analysis`、`stock_analyses[]`、`portfolio_suggestions`

**Markdown**（文件系统）：完整可读报告，按 `reports/YYYY-MM/YYYYMMDD_report_id.md` 组织

## 前端设计

新增「智能投研」导航分组，含三个页面：

1. **市场日报** (`/ai-research/daily`)：最新报告卡片 + 历史列表
2. **个股研究** (`/ai-research/stock`)：标的输入 + 实时进度 + 分析报告
3. **报告历史** (`/ai-research/history`)：筛选 + 对比 + 导出

## 错误处理

| 场景 | 策略 |
|------|------|
| 单个智能体 LLM 失败 | 重试 3 次，仍失败则该维度标记为不可用，整体继续 |
| LLM API 整体不可用 | 报告标记失败，Portal 显示服务不可用 |
| 数据节点超时 | 重试 2 次，使用缓存或有限分析 |
| DuckDB 写入失败 | 文件仍保存，元数据写入失败告警 |
| 新闻 API 不可用 | 降级为仅使用资金流向数据 |
| 总超时 | 55 分钟强制进入综合阶段 |

## 配置

`config/ai_research.yaml`：
- LLM Provider/Model 配置（每个智能体可独立配置）
- API Keys
- 降级策略
- 新闻源配置
- 报告生成参数
- 定时任务配置

## 部署

- Docker Compose 新增 `ai-research` 服务
- `scripts/build.sh` 新增 `lanbao_ai_research`
- `scripts/start_nodes.sh` 启动 `ai_research_node`
- `.env.example` 新增 LLM API Keys

## 测试策略

| 层级 | 工具 | 重点 |
|------|------|------|
| 单元测试 | pytest + pytest-asyncio | LLMClient(Mock)、Prompt 渲染、数据模型 |
| 集成测试 | pytest + launch_testing | Orchestrator 调度、ROS2 Service 调用 |
| 端到端 | Docker Compose | 完整市场日报流程 |

所有 LLM 调用开发测试阶段使用 Mock，CI/CD 强制 Mock。

## 监控

| 监控项 | 采集方式 | 阈值 |
|--------|----------|------|
| 节点状态 | ROS2 /node_status | 离线 > 30s |
| LLM 成功率 | 内部指标 | 失败率 > 20% |
| 报告生成耗时 | 内部指标 | > 50 分钟 |
| Token 消耗 | LLMClient 统计 | 日报 > 100K |
