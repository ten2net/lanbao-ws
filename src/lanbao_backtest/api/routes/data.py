from typing import List, Optional
from fastapi import APIRouter

from ..models import DataSummary, DataTableInfo, SyncTask, QualityReport

router = APIRouter()


class MockDataService:
    """模拟数据服务（后续替换为 DuckDB 真实查询）"""

    @staticmethod
    def get_summary() -> DataSummary:
        return DataSummary(
            total_symbols=5200,
            total_daily_records=12_500_000,
            last_sync_time="2026-05-11 09:00:00",
            coverage_days=252,
        )

    @staticmethod
    def get_tables() -> List[DataTableInfo]:
        return [
            DataTableInfo(name="stock_daily", record_count=12_000_000, date_start="2020-01-01", date_end="2026-05-10", last_updated="2026-05-11 09:00:00", quality_score=98.5),
            DataTableInfo(name="stock_info", record_count=5200, last_updated="2026-05-01 00:00:00", quality_score=100.0),
            DataTableInfo(name="trade_calendar", record_count=1500, last_updated="2026-01-01 00:00:00", quality_score=100.0),
        ]

    @staticmethod
    def get_sync_tasks() -> List[SyncTask]:
        return [
            SyncTask(id="sync-001", source="Tushare", status="success", progress=100.0, success_count=5200, failed_count=0, duration_seconds=180.5),
        ]

    @staticmethod
    def get_quality_report(table: Optional[str] = None) -> List[QualityReport]:
        return [
            QualityReport(table="stock_daily", missing_rate=0.015, coverage_score=98.5, overall_score=98.5),
            QualityReport(table="stock_info", missing_rate=0.0, coverage_score=100.0, overall_score=100.0),
        ]


@router.get("/data/summary", response_model=DataSummary)
async def data_summary():
    return MockDataService.get_summary()


@router.get("/data/tables", response_model=List[DataTableInfo])
async def data_tables():
    return MockDataService.get_tables()


@router.get("/data/sync", response_model=List[SyncTask])
async def sync_status():
    return MockDataService.get_sync_tasks()


@router.post("/data/sync", response_model=SyncTask)
async def trigger_sync(source: Optional[str] = None):
    return SyncTask(id="sync-new", source=source or "Tushare", status="running", progress=0.0, success_count=0, failed_count=0)


@router.get("/data/quality", response_model=List[QualityReport])
async def data_quality(table: Optional[str] = None):
    return MockDataService.get_quality_report(table)
