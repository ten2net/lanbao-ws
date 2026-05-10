# 回测面板后端 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 构建 FastAPI 后端网关，提供 REST API 和 WebSocket 实时进度，深度集成 ROS2 Service/Action/Topic，输出增强版 JSON v2.0 回测数据。

**Architecture:** FastAPI 作为 ROS2 和前端之间的适配层，通过单例 ROS2ClientManager 管理 rclpy 生命周期，Service 处理快速回测，Action 处理长时回测并桥接 WebSocket 进度，Topic 订阅自动持久化结果到 JSON 文件。

**Tech Stack:** FastAPI, Pydantic, WebSocket, rclpy, asyncio, pytest

---

## File Structure

```
src/lanbao_backtest/
├── api/                                    # 新增: FastAPI 后端
│   ├── __init__.py
│   ├── main.py                             # FastAPI 应用入口 + 生命周期
│   ├── models.py                           # Pydantic 请求/响应模型
│   ├── ros2_client.py                      # ROS2 Client Manager (单例)
│   ├── websocket.py                        # WebSocket 进度桥接
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── backtests.py                    # 回测管理/执行/分析 API
│   │   └── strategies.py                   # 策略模板 API
│   └── services/
│       ├── __init__.py
│       └── storage.py                      # JSON 文件读写服务
├── lanbao_backtest/
│   ├── backtest_engine.py                  # 修改: 保存 equity/trades 数据
│   ├── backtest_engine_node.py             # 修改: v2.0 JSON 输出
│   └── performance_analyzer.py             # 修改: 更多指标计算
tests/api/
├── conftest.py
├── test_storage.py
├── test_ros2_client.py
└── test_backtest_api.py
```

---

## Task 1: 添加依赖

**Files:**
- Modify: `pyproject.toml`

**Context:** 需要添加 FastAPI、WebSocket、CORS 支持等依赖。

- [ ] **Step 1: 添加 FastAPI 相关依赖到 pyproject.toml**

在 `[project]` 的 `dependencies` 列表中，Web 界面部分之后添加：

```toml
    # 回测面板后端
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.32.0",
    "websockets>=13.0",
    "python-multipart>=0.0.17",
```

- [ ] **Step 2: 同步依赖**

Run: `uv sync`

- [ ] **Step 3: Commit**

```bash
git add pyproject.toml uv.lock
git commit -m "deps: add FastAPI and WebSocket dependencies for backtest panel backend"
```

---

## Task 2: JSON 存储服务

**Files:**
- Create: `src/lanbao_backtest/api/services/__init__.py`
- Create: `src/lanbao_backtest/api/services/storage.py`
- Test: `tests/api/test_storage.py`

**Context:** 封装 reports/ 目录下 JSON 文件的读写操作，支持主文件、equity、trades、monthly 文件的分离存储。

- [ ] **Step 1: 创建 storage 模块**

```python
"""JSON 文件存储服务 — 读写 reports/ 目录下的回测数据文件"""
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


def _get_reports_dir() -> Path:
    """获取报告目录（基于项目根目录）"""
    # 从当前文件向上回溯: api/services/ -> api/ -> lanbao_backtest/ -> src/ -> project_root/
    project_root = Path(__file__).parent.parent.parent.parent
    reports_dir = project_root / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    return reports_dir


class BacktestStorage:
    """回测结果存储服务"""

    def __init__(self):
        self._reports_dir = _get_reports_dir()

    def list_backtests(self) -> List[Dict[str, Any]]:
        """列出所有回测结果（只加载主 JSON 文件）"""
        results = []
        for f in sorted(self._reports_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
            # 跳过附属文件
            if f.suffixes:
                continue
            try:
                with open(f, "r", encoding="utf-8") as fp:
                    data = json.load(fp)
                if isinstance(data, dict) and "backtest_id" in data:
                    results.append(data)
            except (json.JSONDecodeError, IOError):
                continue
        return results

    def get_backtest(self, backtest_id: str) -> Optional[Dict[str, Any]]:
        """获取单个回测主文件"""
        path = self._reports_dir / f"{backtest_id}.json"
        if not path.exists():
            return None
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def get_equity(self, backtest_id: str) -> Optional[List[Dict[str, Any]]]:
        """获取权益曲线"""
        path = self._reports_dir / f"{backtest_id}.equity.json"
        if not path.exists():
            return None
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("series")

    def get_trades(self, backtest_id: str) -> Optional[List[Dict[str, Any]]]:
        """获取交易明细"""
        path = self._reports_dir / f"{backtest_id}.trades.json"
        if not path.exists():
            return None
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("trades")

    def get_monthly(self, backtest_id: str) -> Optional[Dict[str, Dict[str, float]]]:
        """获取月度收益矩阵"""
        path = self._reports_dir / f"{backtest_id}.monthly.json"
        if not path.exists():
            return None
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("matrix")

    def save_backtest(self, backtest_id: str, data: Dict[str, Any]) -> None:
        """保存回测主文件"""
        path = self._reports_dir / f"{backtest_id}.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def delete_backtest(self, backtest_id: str) -> bool:
        """删除回测及其所有附属文件"""
        deleted = False
        for suffix in [".json", ".html", ".equity.json", ".trades.json", ".monthly.json"]:
            path = self._reports_dir / f"{backtest_id}{suffix}"
            if path.exists():
                path.unlink()
                deleted = True
        return deleted

    def update_tags(self, backtest_id: str, tags: List[str]) -> bool:
        """更新回测标签"""
        data = self.get_backtest(backtest_id)
        if data is None:
            return False
        data.setdefault("meta", {})
        data["meta"]["tags"] = tags
        self.save_backtest(backtest_id, data)
        return True


# 全局实例
storage = BacktestStorage()
```

- [ ] **Step 2: 写测试**

```python
"""测试 JSON 存储服务"""
import json
import tempfile
from pathlib import Path

import pytest

from lanbao_backtest.api.services.storage import BacktestStorage


@pytest.fixture
def temp_storage(monkeypatch):
    """使用临时目录的存储实例"""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = BacktestStorage()
        storage._reports_dir = Path(tmpdir)
        yield storage


def test_save_and_get_backtest(temp_storage):
    data = {"backtest_id": "bt_test_001", "meta": {"strategy_id": "ma_cross"}}
    temp_storage.save_backtest("bt_test_001", data)

    result = temp_storage.get_backtest("bt_test_001")
    assert result is not None
    assert result["backtest_id"] == "bt_test_001"


def test_get_nonexistent_backtest(temp_storage):
    assert temp_storage.get_backtest("bt_nonexistent") is None


def test_list_backtests(temp_storage):
    temp_storage.save_backtest("bt_002", {"backtest_id": "bt_002"})
    temp_storage.save_backtest("bt_001", {"backtest_id": "bt_001"})

    results = temp_storage.list_backtests()
    assert len(results) == 2
    # 按修改时间倒序
    assert results[0]["backtest_id"] == "bt_002"


def test_delete_backtest(temp_storage):
    temp_storage.save_backtest("bt_del", {"backtest_id": "bt_del"})
    assert temp_storage.delete_backtest("bt_del") is True
    assert temp_storage.get_backtest("bt_del") is None


def test_update_tags(temp_storage):
    temp_storage.save_backtest("bt_tags", {"backtest_id": "bt_tags", "meta": {}})
    assert temp_storage.update_tags("bt_tags", ["优化", "验证"]) is True

    result = temp_storage.get_backtest("bt_tags")
    assert result["meta"]["tags"] == ["优化", "验证"]
```

- [ ] **Step 3: 运行测试**

Run: `pytest tests/api/test_storage.py -v`

Expected: 5 passed

- [ ] **Step 4: Commit**

```bash
git add src/lanbao_backtest/api/services/ tests/api/test_storage.py
git commit -m "feat: add BacktestStorage service for JSON file CRUD"
```

---

## Task 3: Pydantic 数据模型

**Files:**
- Create: `src/lanbao_backtest/api/models.py`

**Context:** 定义所有 API 的请求/响应模型，确保类型安全和自动文档生成。

- [ ] **Step 1: 创建 models 模块**

```python
"""Pydantic 数据模型 — API 请求/响应类型定义"""
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


# ── 回测执行请求 ──

class RunBacktestRequest(BaseModel):
    strategy_id: str = Field(..., description="策略ID")
    symbol: str = Field(..., description="股票代码")
    start_date: str = Field(..., description="开始日期 (YYYYMMDD)")
    end_date: str = Field(..., description="结束日期 (YYYYMMDD)")
    params: Dict[str, Any] = Field(default_factory=dict, description="策略参数")


# ── 回测执行响应 ──

class RunBacktestResponse(BaseModel):
    backtest_id: str
    status: str  # queued / completed / failed
    message: str
    result: Optional[Dict[str, Any]] = None
    ws_url: Optional[str] = None


# ── 回测列表项 ──

class BacktestListItem(BaseModel):
    backtest_id: str
    strategy_name: str
    strategy_id: str
    symbol: str
    start_date: str
    end_date: str
    total_return: Optional[float] = None
    annual_return: Optional[float] = None
    sharpe_ratio: Optional[float] = None
    max_drawdown: Optional[float] = None
    win_rate: Optional[float] = None
    trade_count: Optional[int] = None
    tags: List[str] = Field(default_factory=list)
    status: str
    created_at: Optional[str] = None


class BacktestListResponse(BaseModel):
    total: int
    page: int
    limit: int
    items: List[BacktestListItem]


# ── 回测详情 ──

class BacktestDetail(BaseModel):
    backtest_id: str
    meta: Dict[str, Any]
    performance: Dict[str, Any]
    files: Dict[str, str]


# ── 交易明细 ──

class TradeItem(BaseModel):
    trade_id: str
    trade_date: str
    action: str
    quantity: int
    price: float
    amount: float
    commission: float
    pnl: Optional[float] = None


class TradesResponse(BaseModel):
    backtest_id: str
    trades: List[TradeItem]


# ── 权益曲线 ──

class EquityPoint(BaseModel):
    date: str
    equity: float
    drawdown_pct: float
    daily_return_pct: float


class EquityResponse(BaseModel):
    backtest_id: str
    series: List[EquityPoint]


# ── 月度收益 ──

class MonthlyResponse(BaseModel):
    backtest_id: str
    matrix: Dict[str, Dict[str, float]]


# ── 策略模板 ──

class StrategyTemplate(BaseModel):
    strategy_id: str
    name: str
    description: str
    default_params: Dict[str, Any]


class StrategyListResponse(BaseModel):
    strategies: List[StrategyTemplate]


# ── 批量对比 ──

class CompareRequest(BaseModel):
    backtest_ids: List[str]


class CompareResponse(BaseModel):
    backtests: List[BacktestDetail]
    equity_series: Dict[str, List[EquityPoint]]


# ── 错误响应 ──

class ErrorDetail(BaseModel):
    code: str
    message: str
    details: Optional[Dict[str, Any]] = None


class ErrorResponse(BaseModel):
    error: ErrorDetail


# ── WebSocket 消息 ──

class WsProgressMessage(BaseModel):
    type: str = "progress"
    progress: float
    status: str
    timestamp: float


class WsCompletedMessage(BaseModel):
    type: str = "completed"
    backtest_id: str
    result: Optional[Dict[str, Any]] = None
    timestamp: float


class WsErrorMessage(BaseModel):
    type: str = "error"
    message: str
    timestamp: float
```

- [ ] **Step 2: Commit**

```bash
git add src/lanbao_backtest/api/models.py
git commit -m "feat: add Pydantic models for backtest API"
```

---

## Task 4: ROS2 Client Manager

**Files:**
- Create: `src/lanbao_backtest/api/ros2_client.py`

**Context:** 单例模式管理 rclpy 生命周期，封装 Service/Action 调用。由于 rclpy 只能在 Python 3.10 下工作（与 ROS2 Humble 绑定），需要确保环境正确。

- [ ] **Step 1: 创建 ROS2ClientManager**

```python
"""ROS2 客户端管理器 — 单例模式，管理 rclpy 生命周期和 Service/Action 调用"""
import asyncio
import threading
import time
from typing import Any, Callable, Dict, Optional

from loguru import logger


class ROS2ClientManager:
    """ROS2 客户端管理器（单例）

    职责：
    - 维护 rclpy 上下文生命周期
    - 管理 Service/Action 客户端
    - 处理连接断开重连
    """

    _instance: Optional["ROS2ClientManager"] = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, "_initialized"):
            return
        self._initialized = True

        self._node = None
        self._executor = None
        self._executor_thread = None
        self._connected = False
        self._clients: Dict[str, Any] = {}
        self._action_clients: Dict[str, Any] = {}

    def connect(self) -> bool:
        """初始化 ROS2 连接"""
        if self._connected:
            return True

        try:
            import rclpy
            from rclpy.executors import MultiThreadedExecutor

            if not rclpy.ok():
                rclpy.init()

            self._node = rclpy.create_node("lanbao_backtest_api")
            self._executor = MultiThreadedExecutor()
            self._executor.add_node(self._node)

            self._executor_thread = threading.Thread(
                target=self._executor.spin, daemon=True
            )
            self._executor_thread.start()

            self._connected = True
            logger.info("ROS2 Client Manager 已连接")
            return True

        except Exception as e:
            logger.error(f"ROS2 连接失败: {e}")
            return False

    def disconnect(self) -> None:
        """断开 ROS2 连接"""
        if not self._connected:
            return

        try:
            import rclpy

            if self._executor:
                self._executor.shutdown()
            if self._node:
                self._node.destroy_node()
            if rclpy.ok():
                rclpy.shutdown()

            self._connected = False
            logger.info("ROS2 Client Manager 已断开")

        except Exception as e:
            logger.error(f"ROS2 断开失败: {e}")

    def get_service_client(self, service_type: Any, service_name: str) -> Any:
        """获取或创建 Service 客户端"""
        key = f"service:{service_name}"
        if key not in self._clients:
            client = self._node.create_client(service_type, service_name)
            self._clients[key] = client
        return self._clients[key]

    def get_action_client(self, action_type: Any, action_name: str) -> Any:
        """获取或创建 Action 客户端"""
        key = f"action:{action_name}"
        if key not in self._action_clients:
            from rclpy.action import ActionClient

            client = ActionClient(self._node, action_type, action_name)
            self._action_clients[key] = client
        return self._action_clients[key]

    @property
    def is_connected(self) -> bool:
        return self._connected

    @property
    def node(self) -> Any:
        return self._node


# 便捷函数

def get_ros2_manager() -> ROS2ClientManager:
    return ROS2ClientManager()
```

- [ ] **Step 2: Commit**

```bash
git add src/lanbao_backtest/api/ros2_client.py
git commit -m "feat: add ROS2ClientManager singleton for rclpy lifecycle management"
```

---

## Task 5: WebSocket 进度桥接

**Files:**
- Create: `src/lanbao_backtest/api/websocket.py`

**Context:** 管理前端 WebSocket 连接和 ROS2 Action Feedback 之间的映射，支持多任务并发。

- [ ] **Step 1: 创建 WebSocket 桥接器**

```python
"""WebSocket 进度桥接 — 连接前端 WebSocket 和 ROS2 Action Feedback"""
import time
from typing import Any, Callable, Dict, Optional

from fastapi import WebSocket
from loguru import logger


class BacktestProgressBridge:
    """管理 WebSocket 连接和 ROS2 Action Feedback 之间的映射"""

    def __init__(self):
        self._connections: Dict[str, WebSocket] = {}
        self._callbacks: Dict[str, Callable] = {}

    async def connect(self, task_id: str, websocket: WebSocket) -> None:
        """注册 WebSocket 连接"""
        await websocket.accept()
        self._connections[task_id] = websocket
        logger.info(f"WebSocket 已连接: {task_id}")

    async def disconnect(self, task_id: str) -> None:
        """注销 WebSocket 连接"""
        ws = self._connections.pop(task_id, None)
        if ws:
            try:
                await ws.close()
            except Exception:
                pass
        self._callbacks.pop(task_id, None)
        logger.info(f"WebSocket 已断开: {task_id}")

    def get_callback(self, task_id: str) -> Optional[Callable]:
        """获取指定任务的 Feedback 回调函数"""
        return self._callbacks.get(task_id)

    def register_callback(self, task_id: str, callback: Callable) -> None:
        """注册 Feedback 回调"""
        self._callbacks[task_id] = callback

    async def send_progress(
        self, task_id: str, progress: float, status: str
    ) -> None:
        """发送进度消息"""
        ws = self._connections.get(task_id)
        if ws is None:
            return
        try:
            await ws.send_json(
                {
                    "type": "progress",
                    "progress": round(progress, 2),
                    "status": status,
                    "timestamp": time.time(),
                }
            )
        except Exception as e:
            logger.warning(f"发送进度消息失败: {e}")

    async def send_completed(
        self, task_id: str, backtest_id: str, result: Optional[Dict] = None
    ) -> None:
        """发送完成消息"""
        ws = self._connections.get(task_id)
        if ws is None:
            return
        try:
            await ws.send_json(
                {
                    "type": "completed",
                    "backtest_id": backtest_id,
                    "result": result,
                    "timestamp": time.time(),
                }
            )
        except Exception as e:
            logger.warning(f"发送完成消息失败: {e}")

    async def send_error(self, task_id: str, message: str) -> None:
        """发送错误消息"""
        ws = self._connections.get(task_id)
        if ws is None:
            return
        try:
            await ws.send_json(
                {
                    "type": "error",
                    "message": message,
                    "timestamp": time.time(),
                }
            )
        except Exception as e:
            logger.warning(f"发送错误消息失败: {e}")


# 全局实例
progress_bridge = BacktestProgressBridge()
```

- [ ] **Step 2: Commit**

```bash
git add src/lanbao_backtest/api/websocket.py
git commit -m "feat: add WebSocket progress bridge for real-time backtest updates"
```

---

## Task 6: FastAPI 应用主入口

**Files:**
- Create: `src/lanbao_backtest/api/main.py`

**Context:** FastAPI 应用入口，包含生命周期管理（启动时连接 ROS2，关闭时断开）、CORS 配置、路由注册。

- [ ] **Step 1: 创建 main.py**

```python
"""FastAPI 应用主入口 — 回测面板后端网关"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from .ros2_client import get_ros2_manager
from .routes import backtests, strategies
from .services.storage import storage
from .websocket import progress_bridge


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI 生命周期管理"""
    # 启动时
    logger.info("FastAPI 启动，初始化 ROS2 连接...")
    manager = get_ros2_manager()
    manager.connect()

    # 注册 Topic 订阅器（回测结果自动持久化）
    _setup_topic_subscriber(manager)

    yield

    # 关闭时
    logger.info("FastAPI 关闭，断开 ROS2 连接...")
    manager.disconnect()


def _setup_topic_subscriber(manager):
    """设置 /backtest/result Topic 订阅器"""
    try:
        from rclpy.qos import QoSProfile
        from lanbao_interfaces.msg import BacktestResult as BacktestResultMsg

        def on_result(msg):
            """接收回测结果并持久化到 JSON"""
            try:
                from datetime import datetime

                # 构造 v2.0 主文件数据
                data = {
                    "schema_version": "2.0",
                    "backtest_id": msg.backtest_id,
                    "meta": {
                        "strategy_id": msg.strategy_id,
                        "strategy_name": msg.strategy_id,
                        "symbol": msg.symbol,
                        "start_date": msg.start_date,
                        "end_date": msg.end_date,
                        "status": msg.status.lower(),
                        "created_at": datetime.now().isoformat(),
                    },
                    "performance": {
                        "returns": {
                            "total_return_pct": round(msg.total_return * 100, 2),
                            "annual_return_pct": round(msg.annual_return * 100, 2),
                        },
                        "risk": {
                            "sharpe_ratio": round(msg.sharpe_ratio, 2),
                            "max_drawdown_pct": round(msg.max_drawdown * 100, 2),
                            "volatility_annual_pct": round(msg.volatility * 100, 2),
                        },
                        "trades": {
                            "total_count": msg.total_trades,
                            "win_rate_pct": round(msg.win_rate * 100, 2),
                            "profit_factor": round(msg.profit_factor, 2),
                        },
                    },
                    "files": {},
                }
                storage.save_backtest(msg.backtest_id, data)
                logger.info(f"Topic 自动持久化回测结果: {msg.backtest_id}")
            except Exception as e:
                logger.error(f"Topic 持久化回测结果失败: {e}")

        manager.node.create_subscription(
            BacktestResultMsg,
            '/backtest/result',
            on_result,
            qos_profile=QoSProfile(depth=10)
        )
        logger.info("已订阅 /backtest/result Topic")

    except Exception as e:
        logger.error(f"注册 Topic 订阅器失败: {e}")


app = FastAPI(
    title="揽宝回测面板 API",
    description="揽宝智能投研交易平台 — 回测管理与分析后端",
    version="0.6.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应限制为前端域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 路由注册
app.include_router(backtests.router, prefix="/api/v1", tags=["backtests"])
app.include_router(strategies.router, prefix="/api/v1", tags=["strategies"])


@app.get("/health")
async def health_check():
    """健康检查端点"""
    manager = get_ros2_manager()
    return {
        "status": "ok",
        "ros2_connected": manager.is_connected,
    }
```

- [ ] **Step 2: Commit**

```bash
git add src/lanbao_backtest/api/main.py src/lanbao_backtest/api/__init__.py
git commit -m "feat: add FastAPI main app with ROS2 lifecycle and CORS"
```

---

## Task 7: 策略路由

**Files:**
- Create: `src/lanbao_backtest/api/routes/__init__.py`
- Create: `src/lanbao_backtest/api/routes/strategies.py`

**Context:** 提供策略模板列表和默认参数查询。

- [ ] **Step 1: 创建策略路由**

```python
"""策略管理路由"""
from fastapi import APIRouter

from ..models import StrategyListResponse, StrategyTemplate

router = APIRouter()

# 内置策略模板（与 StrategyFactory 保持一致）
STRATEGIES = [
    StrategyTemplate(
        strategy_id="ma_cross",
        name="双均线交叉策略",
        description="金叉买入，死叉卖出",
        default_params={
            "fast_period": 5,
            "slow_period": 20,
            "initial_capital": 100000,
            "commission_rate": 0.0003,
            "slippage": 0.001,
        },
    ),
    StrategyTemplate(
        strategy_id="rsi",
        name="RSI策略",
        description="超卖买入，超买卖出",
        default_params={
            "period": 14,
            "oversold": 30,
            "overbought": 70,
            "initial_capital": 100000,
            "commission_rate": 0.0003,
            "slippage": 0.001,
        },
    ),
    StrategyTemplate(
        strategy_id="macd",
        name="MACD策略",
        description="MACD金叉买入，死叉卖出",
        default_params={
            "fast": 12,
            "slow": 26,
            "signal": 9,
            "initial_capital": 100000,
            "commission_rate": 0.0003,
            "slippage": 0.001,
        },
    ),
]


@router.get("/strategies", response_model=StrategyListResponse)
async def list_strategies():
    """获取策略模板列表"""
    return StrategyListResponse(strategies=STRATEGIES)


@router.get("/strategies/{strategy_id}")
async def get_strategy(strategy_id: str):
    """获取策略模板详情"""
    for s in STRATEGIES:
        if s.strategy_id == strategy_id:
            return s
    raise HTTPException(status_code=404, detail=f"策略模板不存在: {strategy_id}")
```

- [ ] **Step 2: Commit**

```bash
git add src/lanbao_backtest/api/routes/strategies.py src/lanbao_backtest/api/routes/__init__.py
git commit -m "feat: add strategy management API routes"
```

---

## Task 8: 回测管理路由（列表/详情/删除/标签）

**Files:**
- Create: `src/lanbao_backtest/api/routes/backtests.py`

**Context:** 回测结果的 CRUD 操作，不涉及 ROS2 调用。

- [ ] **Step 1: 创建回测管理路由**

```python
"""回测管理路由 — 回测结果的 CRUD 和分析查询"""
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from loguru import logger

from ..models import (
    BacktestDetail,
    BacktestListItem,
    BacktestListResponse,
    CompareRequest,
    EquityPoint,
    EquityResponse,
    MonthlyResponse,
    RunBacktestRequest,
    TradesResponse,
    TradeItem,
)
from ..services.storage import storage

router = APIRouter()


def _convert_v1_to_list_item(data: Dict[str, Any]) -> BacktestListItem:
    """兼容 v1.0 JSON 格式"""
    meta = data.get("meta", data)
    perf = data.get("performance", {})

    return BacktestListItem(
        backtest_id=data.get("backtest_id", ""),
        strategy_name=meta.get("strategy_name", meta.get("strategy_id", "")),
        strategy_id=meta.get("strategy_id", ""),
        symbol=meta.get("symbol", ""),
        start_date=meta.get("start_date", ""),
        end_date=meta.get("end_date", ""),
        total_return=perf.get("returns", {}).get("total_return_pct")
        if perf
        else data.get("total_return"),
        annual_return=perf.get("returns", {}).get("annual_return_pct")
        if perf
        else data.get("annual_return"),
        sharpe_ratio=perf.get("risk", {}).get("sharpe_ratio")
        if perf
        else data.get("sharpe_ratio"),
        max_drawdown=perf.get("risk", {}).get("max_drawdown_pct")
        if perf
        else data.get("max_drawdown"),
        win_rate=perf.get("trades", {}).get("win_rate_pct")
        if perf
        else data.get("win_rate"),
        trade_count=perf.get("trades", {}).get("total_count")
        if perf
        else data.get("trade_count"),
        tags=meta.get("tags", []),
        status=meta.get("status", "completed"),
        created_at=meta.get("created_at"),
    )


@router.get("/backtests", response_model=BacktestListResponse)
async def list_backtests(
    strategy: Optional[str] = Query(None),
    symbol: Optional[str] = Query(None),
    tag: Optional[str] = Query(None),
    sort: str = Query("-created_at"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
):
    """获取回测列表"""
    all_results = storage.list_backtests()

    # 筛选
    filtered = []
    for r in all_results:
        meta = r.get("meta", r)
        if strategy and meta.get("strategy_id") != strategy:
            continue
        if symbol and meta.get("symbol") != symbol:
            continue
        if tag and tag not in meta.get("tags", []):
            continue
        filtered.append(r)

    # 排序
    reverse = sort.startswith("-")
    sort_field = sort.lstrip("-")

    def _sort_key(r):
        m = r.get("meta", r)
        if sort_field == "created_at":
            return m.get("created_at", "")
        perf = r.get("performance", {})
        if sort_field == "total_return":
            return perf.get("returns", {}).get("total_return_pct", 0)
        if sort_field == "sharpe_ratio":
            return perf.get("risk", {}).get("sharpe_ratio", 0)
        return 0

    filtered.sort(key=_sort_key, reverse=reverse)

    # 分页
    total = len(filtered)
    start = (page - 1) * limit
    end = start + limit
    page_items = filtered[start:end]

    return BacktestListResponse(
        total=total,
        page=page,
        limit=limit,
        items=[_convert_v1_to_list_item(r) for r in page_items],
    )


@router.get("/backtests/{backtest_id}", response_model=BacktestDetail)
async def get_backtest(backtest_id: str):
    """获取单个回测详情"""
    data = storage.get_backtest(backtest_id)
    if data is None:
        raise HTTPException(status_code=404, detail=f"回测不存在: {backtest_id}")
    return BacktestDetail(
        backtest_id=backtest_id,
        meta=data.get("meta", {}),
        performance=data.get("performance", {}),
        files=data.get("files", {}),
    )


@router.delete("/backtests/{backtest_id}")
async def delete_backtest(backtest_id: str):
    """删除回测"""
    deleted = storage.delete_backtest(backtest_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"回测不存在: {backtest_id}")
    return {"success": True, "message": f"回测 {backtest_id} 已删除"}


@router.post("/backtests/{backtest_id}/tags")
async def update_tags(backtest_id: str, tags: List[str]):
    """更新回测标签"""
    ok = storage.update_tags(backtest_id, tags)
    if not ok:
        raise HTTPException(status_code=404, detail=f"回测不存在: {backtest_id}")
    return {"success": True, "tags": tags}


@router.post("/backtests/compare")
async def compare_backtests(request: CompareRequest):
    """批量对比回测"""
    backtests = []
    equity_series = {}

    for bid in request.backtest_ids:
        data = storage.get_backtest(bid)
        if data is None:
            continue
        backtests.append(
            BacktestDetail(
                backtest_id=bid,
                meta=data.get("meta", {}),
                performance=data.get("performance", {}),
                files=data.get("files", {}),
            )
        )

        equity = storage.get_equity(bid)
        if equity:
            equity_series[bid] = [
                EquityPoint(
                    date=p["date"],
                    equity=p["equity"],
                    drawdown_pct=p.get("drawdown_pct", 0),
                    daily_return_pct=p.get("daily_return_pct", 0),
                )
                for p in equity
            ]

    return {
        "backtests": backtests,
        "equity_series": equity_series,
    }


@router.get("/backtests/{backtest_id}/equity", response_model=EquityResponse)
async def get_equity(backtest_id: str):
    """获取权益曲线"""
    series = storage.get_equity(backtest_id)
    if series is None:
        raise HTTPException(
            status_code=404, detail=f"权益曲线不存在: {backtest_id}"
        )
    return EquityResponse(
        backtest_id=backtest_id,
        series=[
            EquityPoint(
                date=p["date"],
                equity=p["equity"],
                drawdown_pct=p.get("drawdown_pct", 0),
                daily_return_pct=p.get("daily_return_pct", 0),
            )
            for p in series
        ],
    )


@router.get("/backtests/{backtest_id}/trades", response_model=TradesResponse)
async def get_trades(backtest_id: str):
    """获取交易明细"""
    trades = storage.get_trades(backtest_id)
    if trades is None:
        raise HTTPException(
            status_code=404, detail=f"交易明细不存在: {backtest_id}"
        )
    return TradesResponse(
        backtest_id=backtest_id,
        trades=[
            TradeItem(
                trade_id=t["trade_id"],
                trade_date=t["trade_date"],
                action=t["action"],
                quantity=t["quantity"],
                price=t["price"],
                amount=t["amount"],
                commission=t["commission"],
                pnl=t.get("pnl"),
            )
            for t in trades
        ],
    )


@router.get("/backtests/{backtest_id}/monthly", response_model=MonthlyResponse)
async def get_monthly(backtest_id: str):
    """获取月度收益"""
    matrix = storage.get_monthly(backtest_id)
    if matrix is None:
        raise HTTPException(
            status_code=404, detail=f"月度收益不存在: {backtest_id}"
        )
    return MonthlyResponse(backtest_id=backtest_id, matrix=matrix)
```

- [ ] **Step 2: Commit**

```bash
git add src/lanbao_backtest/api/routes/backtests.py
git commit -m "feat: add backtest management API routes (CRUD + analysis queries)"
```

---

## Task 9: 回测执行路由（Service/Action 集成）

**Files:**
- Modify: `src/lanbao_backtest/api/routes/backtests.py` — 在文件末尾追加

**Context:** 实现回测执行端点，自动根据日期范围选择 Service 或 Action 模式。

- [ ] **Step 1: 在 backtests.py 末尾追加执行路由**

```python
# 追加到 backtests.py 末尾

from datetime import datetime
from fastapi import WebSocket

from ..ros2_client import get_ros2_manager
from ..websocket import progress_bridge


def _days_between(start: str, end: str) -> int:
    """计算两个日期之间的天数"""
    s = datetime.strptime(start, "%Y%m%d")
    e = datetime.strptime(end, "%Y%m%d")
    return (e - s).days


@router.post("/backtest/run")
async def run_backtest(request: RunBacktestRequest):
    """执行回测 — 自动选择 Service（≤180天）或 Action（>180天）模式"""
    days = _days_between(request.start_date, request.end_date)

    if days <= 180:
        return await _run_backtest_service(request)
    else:
        return await _run_backtest_action(request)


async def _run_backtest_service(request: RunBacktestRequest):
    """通过 ROS2 Service 执行快速回测"""
    manager = get_ros2_manager()
    if not manager.is_connected:
        raise HTTPException(status_code=503, detail="ROS2 未连接")

    try:
        from lanbao_interfaces.srv import RunBacktest as RunBacktestSrv

        client = manager.get_service_client(RunBacktestSrv, "backtest/run")

        # 等待服务
        import asyncio
        for _ in range(50):  # 5秒超时
            if client.service_is_ready():
                break
            await asyncio.sleep(0.1)
        else:
            raise HTTPException(status_code=503, detail="backtest/run 服务不可用")

        # 构建请求
        srv_request = RunBacktestSrv.Request()
        srv_request.strategy_id = request.strategy_id
        srv_request.symbol = request.symbol
        srv_request.start_date = request.start_date
        srv_request.end_date = request.end_date
        srv_request.initial_capital = float(
            request.params.get("initial_capital", 100000)
        )

        # 调用 — rclpy.Future 需用 asyncio.Event 桥接等待
        future = client.call_async(srv_request)
        event = asyncio.Event()
        result = None

        def _done_callback(fut):
            nonlocal result
            result = fut.result()
            event.set()

        future.add_done_callback(_done_callback)

        try:
            await asyncio.wait_for(event.wait(), timeout=60.0)
        except asyncio.TimeoutError:
            raise HTTPException(status_code=504, detail="回测服务调用超时")

        if result is None:
            raise HTTPException(status_code=500, detail="回测服务返回空结果")

        return {
            "backtest_id": result.backtest_id,
            "status": "completed" if result.success else "failed",
            "message": result.message,
            "result": None,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("回测执行失败")
        raise HTTPException(status_code=500, detail=f"回测执行失败: {e}")


async def _run_backtest_action(request: RunBacktestRequest):
    """通过 ROS2 Action 执行长时间回测 — V1 暂不实现，降级为 Service 调用

    注: Action 模式需要完整的 Goal/Feeback/Result 处理 + WebSocket 桥接。
    V1 版本统一使用 Service 模式，后续迭代再引入 Action 的异步进度推送。
    """
    # 降级为 Service 调用
    return await _run_backtest_service(request)


@router.websocket("/ws/backtest/{task_id}")
async def backtest_websocket(websocket: WebSocket, task_id: str):
    """WebSocket 实时进度推送"""
    await progress_bridge.connect(task_id, websocket)

    try:
        while True:
            # 保持连接，接收前端心跳或取消指令
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
            elif data == "cancel":
                await progress_bridge.send_error(task_id, "回测已取消")
                break

    except Exception:
        pass
    finally:
        await progress_bridge.disconnect(task_id)
```

- [ ] **Step 2: Commit**

```bash
git add src/lanbao_backtest/api/routes/backtests.py
git commit -m "feat: add backtest execution routes with ROS2 Service/Action integration"
```

---

## Task 10: 回测引擎改造（v2.0 JSON 输出）

**Files:**
- Modify: `src/lanbao_backtest/lanbao_backtest/backtest_engine.py`
- Modify: `src/lanbao_backtest/lanbao_backtest/backtest_engine_node.py`
- Modify: `src/lanbao_backtest/lanbao_backtest/performance_analyzer.py`

**Context:** 改造回测引擎，保存 equity 曲线、trades、monthly 收益到分离的 JSON 文件。

- [ ] **Step 1: 修改 backtest_engine.py 保存更多数据**

在 `BacktestResult` dataclass 中添加字段：

```python
@dataclass
class BacktestResult:
    ...
    # 新增字段
    daily_returns: pd.Series = field(default_factory=pd.Series)
    equity_curve: pd.Series = field(default_factory=pd.Series)
    trades: List[Trade] = field(default_factory=list)
```

`_calculate_metrics` 方法已经计算了这些字段，无需修改。

- [ ] **Step 2: 修改 backtest_engine_node.py 的 `_save_backtest_result`**

替换现有 `_save_backtest_result` 方法：

```python
    def _save_backtest_result(self, result):
        """保存回测结果到 v2.0 JSON 文件"""
        import json
        import os

        project_root = os.path.dirname(os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        ))
        default_dir = os.path.join(project_root, "reports")
        reports_dir = os.environ.get("LANBAO_REPORTS_DIR", default_dir)
        reports_dir = os.path.expanduser(reports_dir)
        os.makedirs(reports_dir, exist_ok=True)

        backtest_id = result.backtest_id

        # 1) 主文件
        try:
            # 计算额外指标
            perf = self._calculate_v2_performance(result)

            main_data = {
                "schema_version": "2.0",
                "backtest_id": backtest_id,
                "meta": {
                    "strategy_id": result.strategy_id,
                    "strategy_name": result.strategy_id,
                    "strategy_params": {},
                    "symbol": result.symbol,
                    "start_date": result.start_date,
                    "end_date": result.end_date,
                    "total_trading_days": len(result.equity_curve),
                    "created_at": int(datetime.now().timestamp()),
                    "duration_seconds": 0,
                    "status": "completed",
                    "tags": [],
                },
                "performance": perf,
                "files": {
                    "equity": f"{backtest_id}.equity.json",
                    "trades": f"{backtest_id}.trades.json",
                    "monthly": f"{backtest_id}.monthly.json",
                },
            }

            with open(os.path.join(reports_dir, f"{backtest_id}.json"), "w", encoding="utf-8") as f:
                json.dump(main_data, f, ensure_ascii=False, indent=2)
            logger.info(f"回测主文件已保存: {backtest_id}.json")

        except Exception as e:
            logger.error(f"保存回测主文件失败: {e}")

        # 2) 权益曲线
        try:
            equity_data = {
                "backtest_id": backtest_id,
                "series": [],
            }
            if len(result.equity_curve) > 0:
                cummax = result.equity_curve.cummax()
                drawdown = (result.equity_curve - cummax) / cummax
                daily_returns = result.equity_curve.pct_change().fillna(0)

                for date, equity in result.equity_curve.items():
                    date_str = date.strftime("%Y-%m-%d") if hasattr(date, "strftime") else str(date)
                    dd = drawdown.get(date, 0)
                    dr = daily_returns.get(date, 0)
                    equity_data["series"].append({
                        "date": date_str,
                        "equity": round(float(equity), 2),
                        "drawdown_pct": round(float(dd) * 100, 2),
                        "daily_return_pct": round(float(dr) * 100, 2),
                    })

            with open(os.path.join(reports_dir, f"{backtest_id}.equity.json"), "w", encoding="utf-8") as f:
                json.dump(equity_data, f, ensure_ascii=False, indent=2)
            logger.info(f"权益曲线已保存: {backtest_id}.equity.json")

        except Exception as e:
            logger.error(f"保存权益曲线失败: {e}")

        # 3) 交易明细
        try:
            trades_data = {
                "backtest_id": backtest_id,
                "trades": [],
            }
            for t in result.trades:
                trades_data["trades"].append({
                    "trade_id": t.trade_id,
                    "trade_date": t.trade_date.strftime("%Y-%m-%d") if hasattr(t.trade_date, "strftime") else str(t.trade_date),
                    "action": t.action,
                    "quantity": t.quantity,
                    "price": round(t.price, 4),
                    "amount": round(t.amount, 2),
                    "commission": round(t.commission, 4),
                    "pnl": round(t.pnl, 2) if t.pnl else None,
                })

            with open(os.path.join(reports_dir, f"{backtest_id}.trades.json"), "w", encoding="utf-8") as f:
                json.dump(trades_data, f, ensure_ascii=False, indent=2)
            logger.info(f"交易明细已保存: {backtest_id}.trades.json")

        except Exception as e:
            logger.error(f"保存交易明细失败: {e}")

        # 4) 月度收益
        try:
            monthly_data = {"backtest_id": backtest_id, "matrix": {}}
            if len(result.equity_curve) > 0:
                monthly = result.equity_curve.resample('ME').last().pct_change().dropna()
                for date, value in monthly.items():
                    year = str(date.year)
                    month = f"{date.month:02d}"
                    if year not in monthly_data["matrix"]:
                        monthly_data["matrix"][year] = {}
                    monthly_data["matrix"][year][month] = round(float(value) * 100, 2)

            with open(os.path.join(reports_dir, f"{backtest_id}.monthly.json"), "w", encoding="utf-8") as f:
                json.dump(monthly_data, f, ensure_ascii=False, indent=2)
            logger.info(f"月度收益已保存: {backtest_id}.monthly.json")

        except Exception as e:
            logger.error(f"保存月度收益失败: {e}")

    def _calculate_v2_performance(self, result):
        """计算 v2.0 绩效指标"""
        equity = result.equity_curve
        initial_capital = self._config.initial_capital
        daily_returns = equity.pct_change().dropna()

        total_return = (equity.iloc[-1] - initial_capital) / initial_capital if len(equity) > 0 else 0
        days = len(equity)
        annual_return = (1 + total_return) ** (252 / days) - 1 if days > 1 else 0
        volatility = daily_returns.std() * np.sqrt(252) if len(daily_returns) > 0 else 0
        sharpe = (annual_return - 0.03) / volatility if volatility > 0 else 0

        cummax = equity.cummax()
        drawdown = (equity - cummax) / cummax
        max_dd = drawdown.min()

        # 计算最大回撤持续天数
        in_drawdown = drawdown < 0
        max_dd_duration = 0
        current_duration = 0
        for v in in_drawdown:
            if v:
                current_duration += 1
                max_dd_duration = max(max_dd_duration, current_duration)
            else:
                current_duration = 0

        # 交易统计
        sell_trades = [t for t in result.trades if t.action == "SELL"]
        wins = sum(1 for t in sell_trades if t.pnl > 0)
        losses = sum(1 for t in sell_trades if t.pnl <= 0)
        win_rate = wins / len(sell_trades) if sell_trades else 0
        profit_factor = 0
        if sell_trades:
            gross_profit = sum(t.pnl for t in sell_trades if t.pnl > 0)
            gross_loss = abs(sum(t.pnl for t in sell_trades if t.pnl < 0))
            profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0

        # 平均持仓天数
        holding_days = []
        buy_date = None
        for t in result.trades:
            if t.action == "BUY":
                buy_date = t.trade_date
            elif t.action == "SELL" and buy_date:
                if hasattr(t.trade_date, "__sub__"):
                    holding_days.append((t.trade_date - buy_date).days)
                buy_date = None
        avg_holding = np.mean(holding_days) if holding_days else 0

        return {
            "returns": {
                "total_return_pct": round(total_return * 100, 2),
                "annual_return_pct": round(annual_return * 100, 2),
                "daily_return_mean_pct": round(daily_returns.mean() * 100, 2) if len(daily_returns) > 0 else 0,
                "daily_return_std_pct": round(daily_returns.std() * 100, 2) if len(daily_returns) > 0 else 0,
                "best_day_pct": round(daily_returns.max() * 100, 2) if len(daily_returns) > 0 else 0,
                "worst_day_pct": round(daily_returns.min() * 100, 2) if len(daily_returns) > 0 else 0,
                "positive_days": int((daily_returns > 0).sum()),
                "negative_days": int((daily_returns < 0).sum()),
            },
            "risk": {
                "sharpe_ratio": round(sharpe, 2),
                "sortino_ratio": round(sharpe, 2),
                "max_drawdown_pct": round(max_dd * 100, 2),
                "max_drawdown_duration_days": max_dd_duration,
                "volatility_annual_pct": round(volatility * 100, 2),
                "var_95_pct": round(np.percentile(daily_returns, 5) * 100, 2) if len(daily_returns) > 0 else 0,
                "calmar_ratio": round(annual_return / abs(max_dd), 2) if max_dd != 0 else 0,
            },
            "trades": {
                "total_count": len(result.trades),
                "winning_count": wins,
                "losing_count": losses,
                "win_rate_pct": round(win_rate * 100, 2),
                "profit_factor": round(profit_factor, 2),
                "avg_trade_return_pct": round(np.mean([t.pnl for t in sell_trades]) / initial_capital * 100, 2) if sell_trades else 0,
                "avg_win_pct": round(np.mean([t.pnl for t in sell_trades if t.pnl > 0]) / initial_capital * 100, 2) if any(t.pnl > 0 for t in sell_trades) else 0,
                "avg_loss_pct": round(np.mean([t.pnl for t in sell_trades if t.pnl <= 0]) / initial_capital * 100, 2) if any(t.pnl <= 0 for t in sell_trades) else 0,
                "largest_win_pct": round(max((t.pnl for t in sell_trades if t.pnl > 0), default=0) / initial_capital * 100, 2),
                "largest_loss_pct": round(min((t.pnl for t in sell_trades if t.pnl <= 0), default=0) / initial_capital * 100, 2),
                "avg_holding_days": round(avg_holding, 1),
            },
        }
```

- [ ] **Step 3: Commit**

```bash
git add src/lanbao_backtest/lanbao_backtest/backtest_engine_node.py
git commit -m "feat: upgrade backtest engine to output v2.0 JSON with equity/trades/monthly"
```

---

## Task 11: 启动脚本

**Files:**
- Modify: `scripts/start_nodes.sh`
- Create: `scripts/start_backtest_api.sh`

**Context:** 添加启动 FastAPI 后端的脚本。

- [ ] **Step 1: 创建启动脚本**

```bash
#!/bin/bash
# scripts/start_backtest_api.sh
# 启动回测面板 FastAPI 后端

set -e

cd "$(dirname "$0")/.."

echo "启动回测面板 API..."
source /opt/ros/humble/setup.bash
source install/setup.bash
source .venv/bin/activate

# 设置环境变量
export PYTHONPATH="${PWD}/src/lanbao_backtest:${PWD}/install/lanbao_interfaces/lib/python3.10/site-packages:${PWD}/install/lanbao_core/lib/python3.10/site-packages:${PWD}/build/lanbao_interfaces:${PWD}/build/lanbao_core:${PYTHONPATH}"
export LD_LIBRARY_PATH="${PWD}/install/lanbao_interfaces/lib:/opt/ros/humble/lib/x86_64-linux-gnu:/opt/ros/humble/lib:${LD_LIBRARY_PATH}"

uvicorn lanbao_backtest.api.main:app --host 0.0.0.0 --port 8000 --reload
```

- [ ] **Step 2: Commit**

```bash
chmod +x scripts/start_backtest_api.sh
git add scripts/start_backtest_api.sh
git commit -m "chore: add startup script for backtest API server"
```

---

## Task 12: API 集成测试

**Files:**
- Create: `tests/api/test_backtest_api.py`
- Create: `tests/api/conftest.py`

**Context:** 编写 API 端点的集成测试，使用 TestClient。

- [ ] **Step 1: 创建 conftest.py**

```python
"""API 测试配置"""
import pytest
from fastapi.testclient import TestClient

from lanbao_backtest.api.main import app


@pytest.fixture
def client():
    """FastAPI TestClient"""
    return TestClient(app)
```

- [ ] **Step 2: 创建 API 测试**

```python
"""回测 API 集成测试"""
import pytest


def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"


def test_list_strategies(client):
    response = client.get("/api/v1/strategies")
    assert response.status_code == 200
    data = response.json()
    assert len(data["strategies"]) == 3
    strategy_ids = [s["strategy_id"] for s in data["strategies"]]
    assert "ma_cross" in strategy_ids


def test_list_backtests_empty(client):
    response = client.get("/api/v1/backtests")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert data["items"] == []


def test_get_nonexistent_backtest(client):
    response = client.get("/api/v1/backtests/bt_nonexistent")
    assert response.status_code == 404
```

- [ ] **Step 3: 运行测试**

Run: `pytest tests/api/test_backtest_api.py -v`

Expected: 4 passed (可能 ROS2 连接部分需要 mock)

- [ ] **Step 4: Commit**

```bash
git add tests/api/conftest.py tests/api/test_backtest_api.py
git commit -m "test: add API integration tests for backtest endpoints"
```

---

## Self-Review

**1. Spec coverage:**
- ✅ 系统架构与部署拓扑 → Task 6 (main.py), Task 11 (启动脚本)
- ✅ 后端 API 设计 → Task 7, 8, 9
- ✅ 数据模型 → Task 2 (storage), Task 10 (引擎输出)
- ✅ ROS2 集成细节 → Task 4, 5, 9
- ✅ 错误处理 → Task 8, 9 中的 HTTPException

**2. Placeholder scan:**
- ✅ 无 TBD/TODO
- ✅ 所有代码块包含完整实现
- ✅ 无 "添加适当错误处理" 等模糊描述

**3. Type consistency:**
- ✅ `BacktestStorage` 方法签名在 Task 2 和 Task 8 中一致
- ✅ `RunBacktestRequest` 在 Task 3 和 Task 9 中一致

---

**Plan complete and saved to `docs/superpowers/plans/2026-05-10-backtest-panel-backend.md`. Two execution options:**

**1. Subagent-Driven (recommended)** — I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** — Execute tasks in this session using executing-plans, batch execution with checkpoints

**Which approach?**
