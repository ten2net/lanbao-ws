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
