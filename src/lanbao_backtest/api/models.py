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


# ── 数据底座 ──

class DataTableInfo(BaseModel):
    name: str
    record_count: int
    date_start: Optional[str] = None
    date_end: Optional[str] = None
    last_updated: Optional[str] = None
    quality_score: float = 100.0


class DataSummary(BaseModel):
    total_symbols: int
    total_daily_records: int
    last_sync_time: Optional[str] = None
    coverage_days: int


class SyncTask(BaseModel):
    id: str
    source: str
    status: str  # running / success / failed
    progress: float
    success_count: int
    failed_count: int
    duration_seconds: Optional[float] = None


class QualityReport(BaseModel):
    table: str
    missing_rate: float
    coverage_score: float
    overall_score: float


# ── 系统配置 ──

class BacktestConfig(BaseModel):
    default_initial_capital: float = 1_000_000.0
    default_commission_rate: float = 0.0003
    default_slippage: float = 0.001
    default_backtest_days: int = 365


class RiskConfig(BaseModel):
    max_single_loss_pct: float = 0.05
    max_drawdown_threshold: float = 0.15
    max_position_pct: float = 0.8
    circuit_breaker_enabled: bool = False


class DataSyncConfig(BaseModel):
    auto_sync_enabled: bool = True
    sync_time: str = "09:00"
    source_priority: str = "tushare > tdx > akshare > miniqmt"


class NotificationConfig(BaseModel):
    webhook_url: Optional[str] = None
    alert_level_threshold: str = "warning"


class SystemConfig(BaseModel):
    backtest: BacktestConfig = Field(default_factory=BacktestConfig)
    risk: RiskConfig = Field(default_factory=RiskConfig)
    data_sync: DataSyncConfig = Field(default_factory=DataSyncConfig)
    notification: NotificationConfig = Field(default_factory=NotificationConfig)
