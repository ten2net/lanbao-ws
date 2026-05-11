from typing import List, Optional
from fastapi import APIRouter
from loguru import logger

from ..models import DataSummary, DataTableInfo, SyncTask, QualityReport
from ..ros2_client import get_ros2_manager

router = APIRouter()


def _get_duckdb_path() -> str:
    """获取 DuckDB 数据库路径"""
    import os
    return os.getenv('DUCKDB_PATH', './data/lanbao.duckdb')


def _query_db(query: str, params: Optional[list] = None):
    """执行 DuckDB 查询"""
    import duckdb
    db_path = _get_duckdb_path()
    conn = None
    try:
        conn = duckdb.connect(db_path, read_only=True)
        if params:
            result = conn.execute(query, params).fetchall()
        else:
            result = conn.execute(query).fetchall()
        return result
    except Exception as e:
        logger.error(f"DuckDB 查询失败: {e}")
        return []
    finally:
        if conn:
            conn.close()


@router.get("/data/summary", response_model=DataSummary)
async def data_summary():
    """数据概览统计"""
    try:
        # 总股票数（stock_daily 中不同 symbol 的数量）
        symbols_result = _query_db("SELECT COUNT(DISTINCT symbol) FROM stock_daily")
        total_symbols = symbols_result[0][0] if symbols_result else 0

        # 日线数据总条数
        daily_result = _query_db("SELECT COUNT(*) FROM stock_daily")
        total_daily = daily_result[0][0] if daily_result else 0

        # 数据起止日期
        range_result = _query_db(
            "SELECT MIN(date), MAX(date) FROM stock_daily"
        )
        date_start = str(range_result[0][0]) if range_result and range_result[0][0] else None
        date_end = str(range_result[0][1]) if range_result and range_result[0][1] else None

        # 覆盖天数
        coverage_days = 0
        if date_start and date_end:
            from datetime import datetime
            try:
                d1 = datetime.strptime(date_start, "%Y-%m-%d")
                d2 = datetime.strptime(date_end, "%Y-%m-%d")
                coverage_days = (d2 - d1).days + 1
            except Exception:
                pass

        # 最后同步时间（从 sync_status 表读取）
        sync_result = _query_db(
            "SELECT last_sync_time FROM sync_status WHERE id = 1"
        )
        last_sync = None
        if sync_result and sync_result[0][0]:
            try:
                last_sync = str(sync_result[0][0])
            except Exception:
                pass

        return DataSummary(
            total_symbols=total_symbols,
            total_daily_records=total_daily,
            last_sync_time=last_sync,
            coverage_days=coverage_days,
        )
    except Exception as e:
        logger.error(f"获取数据概览失败: {e}")
        return DataSummary(
            total_symbols=0,
            total_daily_records=0,
            last_sync_time=None,
            coverage_days=0,
        )


@router.get("/data/tables", response_model=List[DataTableInfo])
async def data_tables():
    """数据表列表及详情"""
    tables = []
    db_path = _get_duckdb_path()
    conn = None
    try:
        import duckdb
        conn = duckdb.connect(db_path, read_only=True)

        # 查询所有用户表
        table_rows = conn.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_schema = 'main'"
        ).fetchall()

        for (table_name,) in table_rows:
            # 查询记录数
            count_result = conn.execute(
                f"SELECT COUNT(*) FROM {table_name}"
            ).fetchone()
            record_count = count_result[0] if count_result else 0

            # 查询日期范围（如果有 date 列）
            date_start = None
            date_end = None
            try:
                cols = conn.execute(
                    f"SELECT column_name FROM information_schema.columns WHERE table_name = '{table_name}'"
                ).fetchall()
                col_names = [c[0] for c in cols]
                if 'date' in col_names:
                    range_result = conn.execute(
                        f"SELECT MIN(date), MAX(date) FROM {table_name}"
                    ).fetchone()
                    date_start = str(range_result[0]) if range_result and range_result[0] else None
                    date_end = str(range_result[1]) if range_result and range_result[1] else None
            except Exception:
                pass

            # 质量评分：简单用数据完整度估算
            quality_score = 100.0
            try:
                if record_count > 0:
                    cols = conn.execute(
                        f"SELECT column_name FROM information_schema.columns WHERE table_name = '{table_name}'"
                    ).fetchall()
                    null_counts = []
                    for (col_name,) in cols:
                        if col_name in ('created_at', 'updated_at', 'data_source'):
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
                        quality_score = max(0.0, 100.0 - (total_nulls / record_count) * 100)
            except Exception:
                pass

            tables.append(DataTableInfo(
                name=table_name,
                record_count=record_count,
                date_start=date_start,
                date_end=date_end,
                last_updated=None,
                quality_score=round(quality_score, 1),
            ))

    except Exception as e:
        logger.error(f"获取数据表列表失败: {e}")
    finally:
        if conn:
            conn.close()

    return tables


@router.get("/data/sync", response_model=List[SyncTask])
async def sync_status():
    """同步状态查询"""
    try:
        result = _query_db(
            "SELECT id, last_sync_time, total_symbols, success_count, failed_count, status, message FROM sync_status WHERE id = 1"
        )
        if result:
            row = result[0]
            return [SyncTask(
                id=f"sync-{row[0]}",
                source="Tushare",
                status=row[5] if row[5] else "idle",
                progress=100.0 if row[5] == "completed" else 0.0,
                success_count=row[3] if row[3] else 0,
                failed_count=row[4] if row[4] else 0,
                duration_seconds=None,
            )]
    except Exception as e:
        logger.error(f"获取同步状态失败: {e}")

    return []


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
                StdString, '/data/trigger_sync', qos_profile=QoSProfile(depth=10)
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
    """数据质量报告"""
    reports = []
    db_path = _get_duckdb_path()
    conn = None
    try:
        import duckdb
        conn = duckdb.connect(db_path, read_only=True)

        # 查询所有用户表
        table_rows = conn.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_schema = 'main'"
        ).fetchall()

        for (table_name,) in table_rows:
            if table and table_name != table:
                continue

            try:
                # 记录数
                count_result = conn.execute(
                    f"SELECT COUNT(*) FROM {table_name}"
                ).fetchone()
                record_count = count_result[0] if count_result else 0

                if record_count == 0:
                    continue

                # 计算缺失率
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

                reports.append(QualityReport(
                    table=table_name,
                    missing_rate=round(missing_rate, 4),
                    coverage_score=round(coverage_score, 1),
                    overall_score=round(overall_score, 1),
                ))
            except Exception as e:
                logger.warning(f"计算 {table_name} 质量失败: {e}")

    except Exception as e:
        logger.error(f"获取数据质量报告失败: {e}")
    finally:
        if conn:
            conn.close()

    return reports
