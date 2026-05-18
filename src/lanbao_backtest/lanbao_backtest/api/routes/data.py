from typing import List, Optional
from fastapi import APIRouter, Path, Query, HTTPException
from loguru import logger

from lanbao_interfaces.srv import GetDataStats, GetDataQuality, GetSyncStatus, GetDataTables, GetTablePreview
from lanbao_interfaces.msg import DataTable
from ..models import DataSummary, DataTableInfo, SyncTask, QualityReport, TablePreviewResponse, ColumnInfo
from ..ros2_client import get_ros2_manager

import json

router = APIRouter()

# ── 内存缓存（Service 不可用时降级使用）──
_data_cache: dict = {
    "summary": None,
    "tables": [],
    "sync_tasks": [],
    "quality": [],
}
_cache_initialized = False


def _call_service(service_type, service_name, request, timeout_sec: float = 10.0):
    """同步调用 ROS2 Service"""
    import rclpy
    manager = get_ros2_manager()
    if not manager.is_connected:
        raise RuntimeError("ROS2 未连接")

    client = manager.get_service_client(service_type, service_name)
    if not client.wait_for_service(timeout_sec=timeout_sec):
        raise TimeoutError(f"Service {service_name} 不可用")

    future = client.call_async(request)
    rclpy.spin_until_future_complete(manager.node, future, timeout_sec=timeout_sec)

    if not future.done():
        raise TimeoutError(f"Service {service_name} 调用超时")

    return future.result()


# ── 缓存刷新逻辑 ──


def _refresh_summary_cache() -> DataSummary:
    """通过 ROS2 Service 刷新概览缓存"""
    try:
        request = GetDataStats.Request()
        response = _call_service(GetDataStats, "data/stats", request)

        if response.success:
            stats = response.stats
            summary = DataSummary(
                total_symbols=stats.total_symbols,
                total_daily_records=stats.total_daily_records or stats.total_records,
                last_sync_time=stats.last_sync_time if stats.last_sync_time else None,
                coverage_days=stats.coverage_days,
            )
            _data_cache["summary"] = summary
            return summary
    except Exception as e:
        logger.error(f"刷新概览缓存失败: {e}")

    if _data_cache["summary"] is None:
        _data_cache["summary"] = DataSummary(
            total_symbols=0,
            total_daily_records=0,
            last_sync_time=None,
            coverage_days=0,
        )
    return _data_cache["summary"]


def _refresh_tables_cache() -> List[DataTableInfo]:
    """通过 ROS2 Service 刷新表列表缓存"""
    try:
        request = GetDataTables.Request()
        response = _call_service(GetDataTables, "data/tables", request)

        if response.success:
            tables = []
            for t in response.tables:
                tables.append(
                    DataTableInfo(
                        name=t.name,
                        record_count=int(t.record_count),
                        date_start=t.date_start if t.date_start else None,
                        date_end=t.date_end if t.date_end else None,
                        last_updated=None,
                        quality_score=t.quality_score,
                    )
                )
            _data_cache["tables"] = tables
            return tables
    except Exception as e:
        logger.error(f"刷新表列表缓存失败: {e}")

    return _data_cache["tables"]


def _refresh_sync_cache() -> List[SyncTask]:
    """通过 ROS2 Service 刷新同步状态缓存"""
    try:
        request = GetSyncStatus.Request()
        response = _call_service(GetSyncStatus, "data/sync_status", request)

        if response.success and response.detail:
            detail = response.detail
            tasks = [
                SyncTask(
                    id="sync-1",
                    source="Tushare",
                    status=detail.status,
                    progress=100.0 if detail.status == "completed" else 0.0,
                    success_count=detail.success_count,
                    failed_count=detail.failed_count,
                    duration_seconds=detail.duration_seconds if detail.duration_seconds > 0 else None,
                )
            ]
            _data_cache["sync_tasks"] = tasks
            return tasks
    except Exception as e:
        logger.error(f"刷新同步状态缓存失败: {e}")

    return _data_cache["sync_tasks"]


def _refresh_quality_cache(table_filter: Optional[str] = None) -> List[QualityReport]:
    """通过 ROS2 Service 刷新质量报告缓存"""
    try:
        request = GetDataQuality.Request()
        response = _call_service(GetDataQuality, "data/quality", request)

        if response.success:
            reports = []
            for item in response.items:
                reports.append(
                    QualityReport(
                        table=item.check_name,
                        missing_rate=0.0,
                        coverage_score=100.0 if item.status == "PASS" else 50.0,
                        overall_score=100.0 if item.status == "PASS" else 50.0,
                    )
                )
            _data_cache["quality"] = reports
            return reports
    except Exception as e:
        logger.error(f"刷新质量缓存失败: {e}")

    return _data_cache["quality"]


def _refresh_all_cache():
    """刷新所有缓存"""
    logger.info("正在刷新数据底座缓存...")
    try:
        _refresh_summary_cache()
    except Exception as e:
        logger.error(f"刷新概览缓存失败: {e}")
    try:
        _refresh_tables_cache()
    except Exception as e:
        logger.error(f"刷新表列表缓存失败: {e}")
    try:
        _refresh_sync_cache()
    except Exception as e:
        logger.error(f"刷新同步状态缓存失败: {e}")
    try:
        _refresh_quality_cache()
    except Exception as e:
        logger.error(f"刷新质量缓存失败: {e}")
    logger.info("数据底座缓存刷新完成")


# 启动后台缓存刷新线程
import threading


def _cache_refresh_loop():
    """后台线程：定期刷新缓存"""
    import time

    while True:
        try:
            time.sleep(60)  # 每60秒刷新一次
            _refresh_all_cache()
        except Exception as e:
            logger.error(f"缓存刷新线程异常: {e}")


# 启动后台线程
cache_thread = threading.Thread(target=_cache_refresh_loop, daemon=True)
cache_thread.start()


# ── API 路由 ──


@router.get("/data/summary", response_model=DataSummary)
async def data_summary():
    """数据概览统计（通过 ROS2 Service 获取）"""
    try:
        return _refresh_summary_cache()
    except Exception as e:
        logger.error(f"获取数据概览失败，使用缓存: {e}")
        if _data_cache["summary"] is not None:
            return _data_cache["summary"]
        return DataSummary(
            total_symbols=0,
            total_daily_records=0,
            last_sync_time=None,
            coverage_days=0,
        )


@router.get("/data/tables", response_model=List[DataTableInfo])
async def data_tables():
    """数据表列表及详情（通过 ROS2 Service 获取）"""
    try:
        return _refresh_tables_cache()
    except Exception as e:
        logger.error(f"获取数据表列表失败，使用缓存: {e}")
        return _data_cache["tables"]


@router.get("/data/sync", response_model=List[SyncTask])
async def sync_status():
    """同步状态查询（通过 ROS2 Service 获取）"""
    try:
        return _refresh_sync_cache()
    except Exception as e:
        logger.error(f"获取同步状态失败，使用缓存: {e}")
        return _data_cache["sync_tasks"]


# 缓存的 Publisher（避免重复创建）
_sync_pub = None


@router.post("/data/sync", response_model=SyncTask)
async def trigger_sync(source: Optional[str] = None):
    """手动触发数据同步"""
    global _sync_pub
    try:
        manager = get_ros2_manager()
        from std_msgs.msg import String as StdString
        from rclpy.qos import QoSProfile

        if _sync_pub is None:
            _sync_pub = manager.node.create_publisher(
                StdString,
                "/data/trigger_sync",
                qos_profile=QoSProfile(depth=10),
            )

        msg = StdString()
        msg.data = f"manual_sync:{source or 'all'}"
        _sync_pub.publish(msg)

        logger.info(f"已发布手动同步触发消息: {msg.data}")
        return SyncTask(
            id="sync-new",
            source=source or "Tushare",
            status="running",
            progress=0.0,
            success_count=0,
            failed_count=0,
            duration_seconds=None,
        )
    except Exception as e:
        logger.error(f"触发同步失败: {e}")
        return SyncTask(
            id="sync-new",
            source=source or "Tushare",
            status="failed",
            progress=0.0,
            success_count=0,
            failed_count=0,
            duration_seconds=None,
        )


@router.get("/data/quality", response_model=List[QualityReport])
async def data_quality(table: Optional[str] = None):
    """数据质量报告（通过 ROS2 Service 获取）"""
    try:
        return _refresh_quality_cache(table)
    except Exception as e:
        logger.error(f"获取数据质量报告失败，使用缓存: {e}")
        if table:
            return [r for r in _data_cache["quality"] if r.table == table]
        return _data_cache["quality"]


@router.get("/data/preview/{table_name}", response_model=TablePreviewResponse)
async def preview_table(
    table_name: str = Path(..., description="表名"),
    limit: int = Query(100, ge=1, le=1000, description="返回行数限制"),
):
    """预览表数据（前 N 行，通过 ROS2 Service 获取）"""
    try:
        request = GetTablePreview.Request()
        request.table_name = table_name
        request.limit = limit
        response = _call_service(GetTablePreview, "data/preview", request)

        if response.success:
            data = json.loads(response.json_data)
            columns = [ColumnInfo(name=c["name"], type=c["type"]) for c in data.get("columns", [])]
            return TablePreviewResponse(
                table=data.get("table", table_name),
                columns=columns,
                rows=data.get("rows", []),
                total=data.get("total", 0),
                limit=data.get("limit", limit),
            )
    except Exception as e:
        logger.error(f"预览表 {table_name} 失败: {e}")

    return TablePreviewResponse(
        table=table_name, columns=[], rows=[], total=0, limit=limit
    )


def _to_tx_code(code: str) -> str:
    """将股票代码转换为腾讯财经格式，支持带后缀格式如 000001.SZ"""
    if not code:
        return ""
    # 去除可能的后缀
    pure_code = code.split(".")[0].split("-")[0].strip()
    prefix = pure_code[:3]
    if prefix in ("600", "601", "603", "605", "688"):
        return f"sh{pure_code}"
    elif prefix in ("000", "001", "002", "003", "300", "301"):
        return f"sz{pure_code}"
    elif prefix in ("430",) or pure_code[0] in ("8", "9"):
        return f"bj{pure_code}"
    else:
        return f"sh{pure_code}"


def _fetch_today_kline(symbol: str) -> tuple[dict | None, str]:
    """调用腾讯财经 API 获取今日实时行情并合成K线数据

    Returns:
        (kline_data, debug_msg): K线数据和调试信息
    """
    import requests
    from datetime import datetime

    tx_code = _to_tx_code(symbol)
    url = f"https://qt.gtimg.cn/q={tx_code}"

    try:
        resp = requests.get(url, timeout=10)
        resp.encoding = "GBK"
        text = resp.text.strip()

        if not text:
            return None, f"腾讯API返回空内容 ({url})"

        for line in text.split(";"):
            line = line.strip()
            if not line.startswith("v_"):
                continue

            try:
                prefix, data = line.split('="', 1)
                data = data.rstrip('"')
                fields = data.split("~")

                if len(fields) < 35:
                    return None, f"腾讯API字段不足: {len(fields)} < 35"

                open_price = float(fields[5]) if fields[5] else 0.0
                high = float(fields[33]) if len(fields) > 33 and fields[33] else 0.0
                low = float(fields[34]) if len(fields) > 34 and fields[34] else 0.0
                close = float(fields[3]) if fields[3] else 0.0
                volume = int(float(fields[6])) if fields[6] else 0

                if close <= 0 or open_price <= 0:
                    return None, f"数据无效: close={close}, open={open_price} (停牌或未开盘)"

                today = datetime.now().strftime("%Y-%m-%d")
                result = {
                    "time": today,
                    "open": round(open_price, 2),
                    "high": round(high, 2),
                    "low": round(low, 2),
                    "close": round(close, 2),
                    "volume": volume,
                }
                return result, "success"
            except (ValueError, IndexError) as e:
                return None, f"解析异常: {e}"

        return None, f"未找到 v_ 开头的数据行"
    except requests.exceptions.Timeout:
        return None, f"请求超时 ({url})"
    except requests.exceptions.ConnectionError as e:
        return None, f"连接失败: {e}"
    except Exception as e:
        return None, f"异常: {type(e).__name__}: {e}"


@router.get("/market/kline/{symbol}")
async def get_kline(
    symbol: str = Path(..., description="股票代码，如 000001.SZ"),
    days: int = Query(30, ge=5, le=365, description="获取最近 N 天的数据"),
):
    """获取股票日K线数据（通过 ROS2 Service 调用 market_data_node），含今日实时数据"""
    from datetime import datetime, timedelta

    kline_data = []
    ros2_success = False

    # 1. 尝试从 ROS2 Service 获取历史数据
    try:
        from lanbao_interfaces.srv import GetMarketData

        end_date = datetime.now().strftime("%Y%m%d")
        start_date = (datetime.now() - timedelta(days=days * 2)).strftime("%Y%m%d")

        req = GetMarketData.Request()
        req.symbol = symbol
        req.start_date = start_date
        req.end_date = end_date

        response = _call_service(GetMarketData, "market_data/get", req, timeout_sec=15.0)

        if response.success:
            for msg in response.data:
                kline_data.append({
                    "time": datetime.fromtimestamp(msg.timestamp / 1000).strftime("%Y-%m-%d"),
                    "open": round(msg.open, 2),
                    "high": round(msg.high, 2),
                    "low": round(msg.low, 2),
                    "close": round(msg.close, 2),
                    "volume": int(msg.volume),
                })
            ros2_success = True
            logger.info(f"ROS2 返回 {symbol} 历史数据 {len(kline_data)} 条")
        else:
            logger.warning(f"ROS2 查询 {symbol} 无数据: {response.message}")
    except Exception as e:
        logger.warning(f"ROS2 查询 {symbol} 失败: {e}")

    # 2. 获取今日实时数据（无论 ROS2 是否成功）
    today_str = datetime.now().strftime("%Y-%m-%d")
    today_kline, today_debug = _fetch_today_kline(symbol)

    if today_kline:
        if kline_data and kline_data[-1]["time"] == today_str:
            kline_data[-1] = today_kline
            logger.info(f"已替换 {symbol} 今日K线为实时数据")
        else:
            kline_data.append(today_kline)
            logger.info(f"已追加 {symbol} 今日实时K线数据")
    else:
        logger.warning(f"{symbol} 今日实时数据不可用: {today_debug}")

    # 3. 返回结果（至少包含今日数据）
    if not kline_data:
        raise HTTPException(status_code=404, detail=f"未找到 {symbol} 的数据（历史数据获取失败且今日数据不可用）")

    return {
        "symbol": symbol,
        "count": len(kline_data),
        "data": kline_data,
        "has_history": ros2_success,
        "has_today": today_kline is not None,
        "today_debug": today_debug,
    }


@router.get("/market/test-tx/{symbol}")
async def test_tencent_api(symbol: str = Path(..., description="股票代码")):
    """测试腾讯财经 API 连通性"""
    today_kline, debug = _fetch_today_kline(symbol)
    return {
        "symbol": symbol,
        "tx_code": _to_tx_code(symbol),
        "success": today_kline is not None,
        "data": today_kline,
        "debug": debug,
        "server_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
