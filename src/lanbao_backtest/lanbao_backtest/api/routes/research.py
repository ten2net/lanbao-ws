"""投研分析 API 路由"""
from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from loguru import logger

from ..ros2_client import get_ros2_manager

router = APIRouter()


class TriggerDailyRequest(BaseModel):
    symbols: Optional[List[str]] = None


class TriggerStockRequest(BaseModel):
    symbol: str


@router.post("/research/market-daily")
async def trigger_market_daily(request: TriggerDailyRequest):
    """触发市场日报分析"""
    try:
        manager = get_ros2_manager()
        from lanbao_interfaces.action import RunResearch

        action_client = manager.node.create_client(RunResearch, '/research/run')
        if not action_client.wait_for_service(timeout_sec=5.0):
            raise HTTPException(status_code=503, detail="AI Research 服务不可用")

        report_id = f"rpt_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        goal = RunResearch.Goal()
        goal.research_type = "market_daily"
        goal.symbols = request.symbols or []
        goal.report_id = report_id

        future = action_client.send_goal_async(goal)

        return {"report_id": report_id, "status": "triggered"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"触发市场日报失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/research/status/{report_id}")
async def get_research_status(report_id: str):
    """获取分析进度"""
    return {
        "report_id": report_id,
        "status": "running",
        "progress": 0.5,
        "message": "分析进行中..."
    }


@router.get("/research/report/{report_id}")
async def get_research_report(report_id: str):
    """获取完整报告"""
    try:
        manager = get_ros2_manager()
        from lanbao_interfaces.srv import GetResearchReport

        client = manager.node.create_client(GetResearchReport, '/research/get_report')
        if not client.wait_for_service(timeout_sec=5.0):
            raise HTTPException(status_code=503, detail="服务不可用")

        request = GetResearchReport.Request()
        request.report_id = report_id

        future = client.call_async(request)
        import rclpy
        rclpy.spin_until_future_complete(manager.node, future, timeout_sec=10.0)

        if not future.done():
            raise HTTPException(status_code=504, detail="查询超时")

        response = future.result()
        if not response.found:
            raise HTTPException(status_code=404, detail="报告不存在")

        import json
        report_data = json.loads(response.report_json)
        return report_data
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取报告失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/research/stock")
async def trigger_stock_research(request: TriggerStockRequest):
    """触发个股深度分析"""
    try:
        manager = get_ros2_manager()
        from lanbao_interfaces.action import RunResearch

        action_client = manager.node.create_client(RunResearch, '/research/run')
        if not action_client.wait_for_service(timeout_sec=5.0):
            raise HTTPException(status_code=503, detail="AI Research 服务不可用")

        report_id = f"rpt_{request.symbol}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        goal = RunResearch.Goal()
        goal.research_type = "stock_analysis"
        goal.symbols = [request.symbol]
        goal.report_id = report_id

        future = action_client.send_goal_async(goal)

        return {"report_id": report_id, "status": "triggered"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"触发个股分析失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/research/reports")
async def list_research_reports(
    report_type: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0)
):
    """获取历史报告列表"""
    from pathlib import Path

    reports = []
    reports_dir = Path("./reports")

    if reports_dir.exists():
        for date_dir in sorted(reports_dir.iterdir(), reverse=True):
            if date_dir.is_dir():
                for file in sorted(date_dir.glob("*.md"), reverse=True):
                    report_id = file.stem
                    reports.append({
                        "report_id": report_id,
                        "created_at": date_dir.name,
                        "path": str(file)
                    })

    total = len(reports)
    reports = reports[offset:offset + limit]

    return {"total": total, "limit": limit, "offset": offset, "reports": reports}
