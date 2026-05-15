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
        if not manager.connect():
            raise HTTPException(status_code=503, detail="ROS2 连接失败，请检查系统是否已启动")
        if manager.node is None:
            raise HTTPException(status_code=503, detail="ROS2 节点未初始化")

        from lanbao_interfaces.action import RunResearch

        action_client = manager.get_action_client(RunResearch, '/research/run')
        if not action_client.wait_for_server(timeout_sec=5.0):
            raise HTTPException(status_code=503, detail="AI Research 服务不可用")

        report_id = f"rpt_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        # 默认分析沪深300核心成分股，确保有实际数据支撑
        default_symbols = [
            "000001", "600519", "000858", "002594",
            "601012", "600036", "000333", "600900",
            "601318", "000002",
        ]
        goal = RunResearch.Goal()
        goal.research_type = "market_daily"
        goal.symbols = request.symbols or default_symbols
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
    """获取分析进度 — 通过检查报告文件是否存在判断状态"""
    from pathlib import Path

    reports_dir = Path("./reports")
    if reports_dir.exists():
        for date_dir in reports_dir.iterdir():
            if date_dir.is_dir():
                report_file = date_dir / f"{report_id}.md"
                if report_file.exists():
                    return {
                        "report_id": report_id,
                        "status": "completed",
                        "progress": 1.0,
                        "message": "分析完成",
                    }

    return {
        "report_id": report_id,
        "status": "running",
        "progress": 0.5,
        "message": "分析进行中...",
    }


@router.get("/research/report/{report_id}")
async def get_research_report(report_id: str):
    """获取完整报告 — 直接读取本地文件，绕过 ROS2 Service 避免超时"""
    from pathlib import Path
    import json

    reports_dir = Path("./reports")
    if reports_dir.exists():
        for date_dir in reports_dir.iterdir():
            if date_dir.is_dir():
                # 优先读取 JSON
                json_file = date_dir / f"{report_id}.json"
                if json_file.exists():
                    return json.loads(json_file.read_text(encoding='utf-8'))
                # 回退到 markdown
                md_file = date_dir / f"{report_id}.md"
                if md_file.exists():
                    markdown = md_file.read_text(encoding='utf-8')
                    return {
                        "report_id": report_id,
                        "report_type": "market_daily",
                        "created_at": "",
                        "summary": {
                            "market_trend": markdown[:2000],
                            "overall_verdict": "HOLD",
                            "confidence": 0.5,
                            "top_sectors": [],
                            "risk_level": "中"
                        },
                        "stock_analyses": [],
                        "portfolio_suggestions": {}
                    }

    raise HTTPException(status_code=404, detail="报告不存在")


@router.post("/research/stock")
async def trigger_stock_research(request: TriggerStockRequest):
    """触发个股深度分析"""
    try:
        manager = get_ros2_manager()
        if not manager.connect():
            raise HTTPException(status_code=503, detail="ROS2 连接失败，请检查系统是否已启动")
        if manager.node is None:
            raise HTTPException(status_code=503, detail="ROS2 节点未初始化")

        from lanbao_interfaces.action import RunResearch

        action_client = manager.get_action_client(RunResearch, '/research/run')
        if not action_client.wait_for_server(timeout_sec=5.0):
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
