# CompositeStrategy + AIResearchStrategy 设计方案

日期: 2026-05-13
分支: feat/ai-strategy-signals

## 背景

将 Phase 1 的 AI 智能投研报告接入 Phase 2 的策略信号系统，采用"信号叠加器架构"（CompositeStrategy）。AI 投研评级作为一等公民策略，与传统技术指标策略共同参与加权投票。

## 架构设计

### 1. CompositeStrategy（组合策略 / 信号叠加器）

- **职责**: 聚合多个子策略的信号，通过加权投票产生最终交易决策
- **文件**: `src/lanbao_strategy/lanbao_strategy/composite_strategy.py`

**投票模式**:

| 模式 | 说明 |
|------|------|
| `weighted_sum`（默认） | 信号映射为数值后加权求和，根据阈值判断 BUY/SELL/HOLD |
| `majority` | BUY/SELL 按权重计票，需超过 `min_confidence` 比例 |
| `unanimous` | 所有活跃信号方向必须一致，且置信度达标 |

**信号映射**:
- BUY/STRONG_BUY → +1, SELL/STRONG_SELL → -1, HOLD → 0
- 支持负权重（反向信号）
- 支持嵌套 CompositeStrategy

**核心公式（weighted_sum）**:
```
final_score = Σ(signal_i × weight_i × strength_i) / Σ|weight_i|
if final_score >= threshold_buy:  → BUY
if final_score <= threshold_sell: → SELL
else:                             → 无信号
```

### 2. AIResearchStrategy（AI 投研策略）

- **职责**: 将 AI 投研报告（ResearchReport）转换为交易信号
- **文件**: `src/lanbao_strategy/lanbao_strategy/ai_research_strategy.py`

**评级映射**:

| Verdict | 信号 | 基础强度 |
|---------|------|---------|
| STRONG_BUY | BUY | 1.0 |
| BUY | BUY | 0.7 |
| HOLD | HOLD | 0.0 |
| SELL | SELL | 0.7 |
| STRONG_SELL | SELL | 1.0 |

**强度公式**:
```
strength = base_strength × confidence × (score / 100) × decay_factor
```

**降级机制**:
- 未设置 report_provider → HOLD（fallback）
- provider 返回 None/异常 → HOLD
- 报告过期（> expiry_hours）→ 线性衰减至 0
- 无个股分析 → 使用 summary 整体评级

**数据获取**: 通过注入的 `report_provider` 回调获取报告，松耦合设计，不直接依赖 ROS2。

### 3. StrategyFactory 扩展

新增两个模板注册:

| 模板 ID | 类 |
|---------|-----|
| `composite` | `CompositeStrategy` |
| `ai_research` | `AIResearchStrategy` |

**Composite 配置示例**:
```python
{
    "template_id": "composite",
    "strategy_id": "comp_001",
    "params": {
        "sub_strategies": [
            {"template_id": "ma_cross", "strategy_id": "ma", "weight": 0.3},
            {"template_id": "macd", "strategy_id": "macd", "weight": 0.2},
            {"template_id": "ai_research", "strategy_id": "ai", "weight": 0.5,
             "params": {"symbol": "600519"}},
        ],
        "voting_mode": "weighted_sum",
        "threshold_buy": 0.15,
        "threshold_sell": -0.15,
    }
}
```

### 4. 运行时数据流

```
MarketDataNode → K线数据 → StrategyManagerNode
                            ↓
                  CompositeStrategy.on_data()
                            ↓
              ┌───────────────┼───────────────┐
              ↓               ↓               ↓
        MA.on_data()    RSI.on_data()   AIResearch.on_data()
              ↓               ↓               ↓
          Signal(BUY)   Signal(HOLD)    Signal(BUY, s=0.8)
              └───────────────┴───────────────┘
                            ↓
                  加权聚合: 0.3×1×0.8 + 0.2×0 + 0.5×1×0.8 = 0.64
                            ↓
                  Signal(BUY, strength=0.64)
                            ↓
                  Publish TradeSignal.msg
```

## 测试覆盖

| 测试文件 | 用例数 | 覆盖内容 |
|---------|--------|---------|
| `test_composite_strategy.py` | 24 | 初始化、加权和、多数决、一致通过、负权重、嵌套、边界 |
| `test_ai_research_strategy.py` | 25 | 评级映射、强度计算、降级、过期衰减、刷新间隔、Pydantic 支持 |
| `test_strategy_factory.py` | 18 | 模板注册、创建、参数验证、嵌套 composite、错误处理 |

**总计**: 67 个测试，全部通过。

## 实现文件清单

- `src/lanbao_strategy/lanbao_strategy/composite_strategy.py` — 新增
- `src/lanbao_strategy/lanbao_strategy/ai_research_strategy.py` — 新增
- `src/lanbao_strategy/lanbao_strategy/strategy_factory.py` — 扩展
- `src/lanbao_strategy/lanbao_strategy/__init__.py` — 扩展导出
- `tests/test_strategy/test_composite_strategy.py` — 新增
- `tests/test_strategy/test_ai_research_strategy.py` — 新增
- `tests/test_strategy/test_strategy_factory.py` — 新增

## 注意事项

1. **Pydantic v2 Enum**: `model_dump()` 嵌套模型时枚举不会自动转字符串，代码中已做 `verdict.value` 处理
2. **回测兼容**: CompositeStrategy 提供 `to_signal_generator()` 方法，返回 `Callable[[DataFrame], Series]` 适配现有回测引擎
3. **ROS2 集成**: AIResearchStrategy 通过注入 `report_provider` 获取报告，ROS2 节点负责将 Service client 包装为 provider 回调
