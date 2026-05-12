"""回测管理路由 — 回测结果的 CRUD、分析和执行"""
import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query, WebSocket
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
from ..ros2_client import get_ros2_manager
from ..services.storage import storage
from ..websocket import progress_bridge

router = APIRouter()


# ── 辅助函数 ──

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


def _days_between(start: str, end: str) -> int:
    """计算两个日期之间的天数"""
    s = datetime.strptime(start, "%Y%m%d")
    e = datetime.strptime(end, "%Y%m%d")
    return (e - s).days


# ── 回测管理 ──

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


# ── 回测分析 ──

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


# ── 回测执行 ──

@router.post("/backtest/run")
async def run_backtest(request: RunBacktestRequest):
    """执行回测 — V1 统一使用 ROS2 Service 模式"""
    return await _run_backtest_service(request)


async def _run_backtest_service(request: RunBacktestRequest):
    """通过 ROS2 Service 执行回测"""
    manager = get_ros2_manager()
    if not manager.is_connected:
        raise HTTPException(status_code=503, detail="ROS2 未连接")

    try:
        from lanbao_interfaces.srv import RunBacktest as RunBacktestSrv

        client = manager.get_service_client(RunBacktestSrv, "backtest/run")

        # 等待服务就绪
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


# ── WebSocket ──

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
