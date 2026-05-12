from typing import List, Optional
from fastapi import APIRouter, Path, Query
from loguru import logger

from lanbao_data.duckdb_lock import db_lock
from ..models import DataSummary, DataTableInfo, SyncTask, QualityReport, TablePreviewResponse, ColumnInfo
from ..ros2_client import get_ros2_manager

router = APIRouter()

# ── 内存缓存（同步期间数据库被锁定时使用）──
_data_cache: dict = {
    "summary": None,
    "tables": [],
    "sync_tasks": [],
    "quality": [],
}
_cache_initialized = False


def _get_duckdb_path() -> str:
    """获取 DuckDB 数据库路径（返回绝对路径）"""
    import os
    from pathlib import Path

    env_path = os.getenv("DUCKDB_PATH")
    if env_path:
        return str(Path(env_path).resolve())

    # 从当前文件位置推算工作空间根目录
    current_file = Path(__file__).resolve()
    # data.py -> routes -> api -> lanbao_backtest -> src -> workspace_root
    workspace_root = current_file.parent.parent.parent.parent.parent
    db_path = workspace_root / "data" / "lanbao.duckdb"
    if db_path.exists():
        return str(db_path)

    # 回退：尝试从当前工作目录向上查找
    cwd = Path(os.getcwd()).resolve()
    for parent in [cwd] + list(cwd.parents):
        candidate = parent / "data" / "lanbao.duckdb"
        if candidate.exists():
            return str(candidate)

    # 最终回退到工作空间根目录
    return str(db_path)


def _query_db(query: str, params: Optional[list] = None):
    """执行 DuckDB 查询（通过文件锁协调多进程访问）"""
    import duckdb

    db_path = _get_duckdb_path()
    conn = None
    try:
        with db_lock(db_path, mode="shared", timeout=60.0):
            conn = duckdb.connect(db_path, read_only=True)
            if params:
                result = conn.execute(query, params).fetchall()
            else:
                result = conn.execute(query).fetchall()
            return result
    except TimeoutError as e:
        logger.warning(f"获取数据库读锁超时: {e}")
        return []
    except Exception as e:
        logger.error(f"DuckDB 查询失败: {e}")
        return []
    finally:
        if conn:
            try:
                conn.close()
            except Exception:
                pass


# ── 缓存刷新逻辑 ──


def _refresh_summary_cache() -> DataSummary:
    """从 DuckDB 刷新概览缓存"""
    try:
        symbols_result = _query_db(
            "SELECT COUNT(DISTINCT symbol) FROM stock_daily"
        )
        total_symbols = symbols_result[0][0] if symbols_result else 0

        daily_result = _query_db("SELECT COUNT(*) FROM stock_daily")
        total_daily = daily_result[0][0] if daily_result else 0

        range_result = _query_db("SELECT MIN(date), MAX(date) FROM stock_daily")
        date_start = (
            str(range_result[0][0])
            if range_result and range_result[0][0]
            else None
        )
        date_end = (
            str(range_result[0][1])
            if range_result and range_result[0][1]
            else None
        )

        coverage_days = 0
        if date_start and date_end:
            from datetime import datetime
            try:
                d1 = datetime.strptime(date_start, "%Y-%m-%d")
                d2 = datetime.strptime(date_end, "%Y-%m-%d")
                coverage_days = (d2 - d1).days + 1
            except Exception:
                pass

        sync_result = _query_db(
            "SELECT last_sync_time FROM sync_status WHERE id = 1"
        )
        last_sync = None
        if sync_result and sync_result[0][0]:
            try:
                last_sync = str(sync_result[0][0])
            except Exception:
                pass

        summary = DataSummary(
            total_symbols=total_symbols,
            total_daily_records=total_daily,
            last_sync_time=last_sync,
            coverage_days=coverage_days,
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
    """从 DuckDB 刷新表列表缓存"""
    tables = []
    db_path = _get_duckdb_path()
    try:
        import duckdb
        with db_lock(db_path, mode="shared", timeout=60.0):
            conn = duckdb.connect(db_path, read_only=True)
            try:
                table_rows = conn.execute(
                    "SELECT table_name FROM information_schema.tables WHERE table_schema = 'main'"
                ).fetchall()

                for (table_name,) in table_rows:
                    try:
                        count_result = conn.execute(
                            f"SELECT COUNT(*) FROM {table_name}"
                        ).fetchone()
                        record_count = count_result[0] if count_result else 0

                        date_start = None
                        date_end = None
                        try:
                            cols = conn.execute(
                                f"SELECT column_name FROM information_schema.columns WHERE table_name = '{table_name}'"
                            ).fetchall()
                            col_names = [c[0] for c in cols]
                            if "date" in col_names:
                                range_result = conn.execute(
                                    f"SELECT MIN(date), MAX(date) FROM {table_name}"
                                ).fetchone()
                                date_start = (
                                    str(range_result[0])
                                    if range_result and range_result[0]
                                    else None
                                )
                                date_end = (
                                    str(range_result[1])
                                    if range_result and range_result[1]
                                    else None
                                )
                        except Exception:
                            pass

                        quality_score = 100.0
                        if record_count > 0:
                            try:
                                cols = conn.execute(
                                    f"SELECT column_name FROM information_schema.columns WHERE table_name = '{table_name}'"
                                ).fetchall()
                                null_counts = []
                                for (col_name,) in cols:
                                    if col_name in ("created_at", "updated_at", "data_source"):
                                        continue
                                    try:
                                        null_result = conn.execute(
                                            f"SELECT COUNT(*) FROM {table_name} WHERE {col_name} IS NULL"
                                        ).fetchone()
                                        null_counts.append(null_result[0])
                                    except Exception:
                                        pass
                                total_nulls = sum(null_counts)
                                if total_nulls > 0:
                                    quality_score = max(
                                        0.0, 100.0 - (total_nulls / record_count) * 100
                                    )
                            except Exception:
                                pass

                        tables.append(
                            DataTableInfo(
                                name=table_name,
                                record_count=record_count,
                                date_start=date_start,
                                date_end=date_end,
                                last_updated=None,
                                quality_score=round(quality_score, 1),
                            )
                        )
                    except Exception as e:
                        logger.warning(f"处理表 {table_name} 失败: {e}")
            finally:
                conn.close()

    except TimeoutError as e:
        logger.warning(f"刷新表列表缓存时获取读锁超时: {e}")
    except Exception as e:
        logger.error(f"刷新表列表缓存失败: {e}")

    if tables:
        _data_cache["tables"] = tables
    return _data_cache["tables"]


def _refresh_sync_cache() -> List[SyncTask]:
    """从 DuckDB 刷新同步状态缓存"""
    try:
        result = _query_db(
            "SELECT id, last_sync_time, total_symbols, success_count, failed_count, status, message FROM sync_status WHERE id = 1"
        )
        if result:
            row = result[0]
            tasks = [
                SyncTask(
                    id=f"sync-{row[0]}",
                    source="Tushare",
                    status=row[5] if row[5] else "idle",
                    progress=100.0 if row[5] == "completed" else 0.0,
                    success_count=row[3] if row[3] else 0,
                    failed_count=row[4] if row[4] else 0,
                    duration_seconds=None,
                )
            ]
            _data_cache["sync_tasks"] = tasks
            return tasks
    except Exception as e:
        logger.error(f"刷新同步状态缓存失败: {e}")

    return _data_cache["sync_tasks"]


def _refresh_quality_cache(table_filter: Optional[str] = None) -> List[QualityReport]:
    """从 DuckDB 刷新质量报告缓存"""
    reports = []
    db_path = _get_duckdb_path()
    try:
        import duckdb
        with db_lock(db_path, mode="shared", timeout=60.0):
            conn = duckdb.connect(db_path, read_only=True)
            try:
                table_rows = conn.execute(
                    "SELECT table_name FROM information_schema.tables WHERE table_schema = 'main'"
                ).fetchall()

                for (table_name,) in table_rows:
                    if table_filter and table_name != table_filter:
                        continue
                    try:
                        count_result = conn.execute(
                            f"SELECT COUNT(*) FROM {table_name}"
                        ).fetchone()
                        record_count = count_result[0] if count_result else 0
                        if record_count == 0:
                            continue

                        cols = conn.execute(
                            f"SELECT column_name FROM information_schema.columns WHERE table_name = '{table_name}'"
                        ).fetchall()
                        total_cells = record_count * len(cols)
                        null_cells = 0
                        for (col_name,) in cols:
                            try:
                                null_result = conn.execute(
                                    f"SELECT COUNT(*) FROM {table_name} WHERE {col_name} IS NULL"
                                ).fetchone()
                                null_cells += null_result[0]
                            except Exception:
                                pass

                        missing_rate = null_cells / total_cells if total_cells > 0 else 0.0
                        coverage_score = max(0.0, 100.0 - missing_rate * 100)
                        overall_score = coverage_score

                        reports.append(
                            QualityReport(
                                table=table_name,
                                missing_rate=round(missing_rate, 4),
                                coverage_score=round(coverage_score, 1),
                                overall_score=round(overall_score, 1),
                            )
                        )
                    except Exception as e:
                        logger.warning(f"计算 {table_name} 质量失败: {e}")
            finally:
                conn.close()

    except TimeoutError as e:
        logger.warning(f"刷新质量缓存时获取读锁超时: {e}")
    except Exception as e:
        logger.error(f"刷新质量缓存失败: {e}")

    if reports:
        _data_cache["quality"] = reports
    return _data_cache["quality"]


def _refresh_all_cache():
    """刷新所有缓存"""
    logger.info("正在刷新数据底座缓存...")
    _refresh_summary_cache()
    _refresh_tables_cache()
    _refresh_sync_cache()
    _refresh_quality_cache()
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


# 立即初始化缓存
try:
    _refresh_all_cache()
    _cache_initialized = True
    logger.info("数据底座缓存初始化完成")
except Exception as e:
    logger.error(f"缓存初始化失败: {e}")

# 启动后台线程
cache_thread = threading.Thread(target=_cache_refresh_loop, daemon=True)
cache_thread.start()


# ── API 路由 ──


@router.get("/data/summary", response_model=DataSummary)
async def data_summary():
    """数据概览统计（优先缓存，失败回退）"""
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
    """数据表列表及详情（优先缓存，失败回退）"""
    try:
        return _refresh_tables_cache()
    except Exception as e:
        logger.error(f"获取数据表列表失败，使用缓存: {e}")
        return _data_cache["tables"]


@router.get("/data/sync", response_model=List[SyncTask])
async def sync_status():
    """同步状态查询（优先缓存，失败回退）"""
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
    """数据质量报告（优先缓存，失败回退）"""
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
    """预览表数据（前 N 行）"""
    db_path = _get_duckdb_path()
    try:
        import duckdb
        with db_lock(db_path, mode="shared", timeout=60.0):
            conn = duckdb.connect(db_path, read_only=True)
            try:
                # 验证表存在
                tables = conn.execute(
                    "SELECT table_name FROM information_schema.tables WHERE table_schema = 'main'"
                ).fetchall()
                if table_name not in [t[0] for t in tables]:
                    return TablePreviewResponse(
                        table=table_name, columns=[], rows=[], total=0, limit=limit
                    )

                # 获取列信息
                cols = conn.execute(
                    "SELECT column_name, data_type FROM information_schema.columns "
                    f"WHERE table_name = '{table_name}' ORDER BY ordinal_position"
                ).fetchall()
                columns = [ColumnInfo(name=c[0], type=c[1] or "UNKNOWN") for c in cols]

                # 获取总行数
                count_result = conn.execute(
                    f"SELECT COUNT(*) FROM {table_name}"
                ).fetchone()
                total = count_result[0] if count_result else 0

                # 获取前 N 行
                rows = conn.execute(
                    f"SELECT * FROM {table_name} LIMIT {limit}"
                ).fetchall()

                # 将 Decimal/datetime 等转为可 JSON 序列化的类型
                serializable_rows = []
                for row in rows:
                    new_row = []
                    for val in row:
                        if val is None:
                            new_row.append(None)
                        elif hasattr(val, "isoformat"):
                            new_row.append(val.isoformat())
                        elif hasattr(val, "__float__"):
                            new_row.append(float(val))
                        elif hasattr(val, "__int__") and not isinstance(val, bool):
                            new_row.append(int(val))
                        else:
                            new_row.append(val)
                    serializable_rows.append(new_row)

                return TablePreviewResponse(
                    table=table_name,
                    columns=columns,
                    rows=serializable_rows,
                    total=total,
                    limit=limit,
                )
            finally:
                conn.close()

    except TimeoutError as e:
        logger.warning(f"预览表 {table_name} 时获取读锁超时: {e}")
        return TablePreviewResponse(
            table=table_name, columns=[], rows=[], total=0, limit=limit
        )
    except Exception as e:
        logger.error(f"预览表 {table_name} 失败: {e}")
        return TablePreviewResponse(
            table=table_name, columns=[], rows=[], total=0, limit=limit
        )
