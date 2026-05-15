"""自选股管理 API 路由"""
from typing import List, Optional, Dict
from datetime import datetime

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from loguru import logger

from ..ros2_client import get_ros2_manager

router = APIRouter()


class FavorConditionCreate(BaseModel):
    name: str
    query: str
    description: str = ""
    enabled: bool = True
    priority: int = 0
    max_results: int = 15
    filter_hot_sector: bool = False
    filter_min_cap_yi: Optional[float] = None


class FavorConditionResponse(BaseModel):
    id: int
    name: str
    query: str
    description: str = ""
    enabled: bool = True
    priority: int = 0
    max_results: int = 15
    filter_hot_sector: bool = False
    filter_min_cap_yi: Optional[float] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class FavorPickRequest(BaseModel):
    condition_names: Optional[List[str]] = None
    clear_existing: bool = False
    account_id: str = "default"


class FavorPickResponse(BaseModel):
    success: bool
    message: str
    total_unique: int
    added: int
    existing: int
    codes: List[str]


class WatchlistAddRequest(BaseModel):
    code: str
    name: str = ""
    account_id: str = "default"
    group_name: str = "自选股"
    source_condition: str = ""


class WatchlistItemResponse(BaseModel):
    code: str
    name: str = ""
    account_id: str = "default"
    group_name: str = "自选股"
    source_condition: str = ""
    signal_type: str = ""
    confidence: float = 0.0
    added_at: Optional[str] = None


def _call_ros2_service(service_type, service_name: str, request, timeout_sec: float = 10.0):
    """同步调用 ROS2 Service"""
    import rclpy
    manager = get_ros2_manager()
    if not manager.is_connected:
        raise RuntimeError("ROS2 未连接")

    client = manager.node.create_client(service_type, service_name)
    if not client.wait_for_service(timeout_sec=5.0):
        raise TimeoutError(f"Service {service_name} 不可用")

    future = client.call_async(request)
    rclpy.spin_until_future_complete(manager.node, future, timeout_sec=timeout_sec)

    if not future.done():
        raise TimeoutError(f"Service {service_name} 调用超时")

    return future.result()


def _to_tx_code(code: str) -> str:
    """将纯数字代码转换为腾讯财经格式"""
    if not code:
        return ""
    prefix = code[:3]
    if prefix in ('600', '601', '603', '605', '688'):
        return f"sh{code}"
    elif prefix in ('000', '001', '002', '003', '300', '301'):
        return f"sz{code}"
    elif prefix in ('430',) or code[0] in ('8', '9'):
        return f"bj{code}"
    else:
        return f"sh{code}"


def _fetch_tx_quotes(codes: List[str]) -> Dict[str, Dict]:
    """调用腾讯财经 API 获取实时行情"""
    import requests

    if not codes:
        return {}

    tx_codes = [_to_tx_code(c) for c in codes]
    url = f"https://qt.gtimg.cn/q={','.join(tx_codes)}"

    try:
        resp = requests.get(url, timeout=10)
        resp.encoding = 'GBK'
        text = resp.text.strip()

        quotes: Dict[str, Dict] = {}
        for line in text.split(';'):
            line = line.strip()
            if not line.startswith('v_'):
                continue

            try:
                prefix, data = line.split('="', 1)
                tx_code = prefix.split('_')[1]
                code = tx_code.replace('sh', '').replace('sz', '').replace('bj', '')
                data = data.rstrip('"')
                fields = data.split('~')

                if len(fields) < 35:
                    continue

                price = float(fields[3]) if fields[3] else 0.0
                change = float(fields[31]) if fields[31] else 0.0
                change_pct = float(fields[32]) if fields[32] else 0.0
                high = float(fields[33]) if fields[33] else 0.0
                low = float(fields[34]) if fields[34] else 0.0

                quotes[code] = {
                    'name': fields[1],
                    'price': price,
                    'change': change,
                    'change_pct': change_pct,
                    'high': high,
                    'low': low,
                }
            except (ValueError, IndexError):
                continue

        return quotes
    except Exception as e:
        logger.warning(f"获取腾讯行情失败: {e}")
        return {}


@router.post("/favor/pick", response_model=FavorPickResponse)
async def favor_pick(request: FavorPickRequest):
    """执行选股并加入自选股"""
    try:
        from lanbao_interfaces.srv import FavorPick

        req = FavorPick.Request()
        req.condition_names = request.condition_names or []
        req.clear_existing = request.clear_existing
        req.account_id = request.account_id

        response = _call_ros2_service(FavorPick, "/favor/pick", req, timeout_sec=30.0)

        return FavorPickResponse(
            success=response.success,
            message=response.message,
            total_unique=response.total_unique,
            added=response.added,
            existing=response.existing,
            codes=list(response.codes),
        )
    except HTTPException:
        raise
    except TimeoutError as e:
        logger.error(f"选股超时: {e}")
        raise HTTPException(status_code=504, detail=str(e))
    except Exception as e:
        logger.error(f"选股失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/favor/watchlist", response_model=List[WatchlistItemResponse])
async def get_watchlist(
    account_id: Optional[str] = Query("default"),
    group_name: Optional[str] = Query(None),
):
    """获取自选股列表（通过 ROS2 Service 调用 favor_node）"""
    try:
        from lanbao_interfaces.srv import FavorGetWatchlist

        req = FavorGetWatchlist.Request()
        req.account_id = account_id or ""
        req.group_name = group_name or ""

        response = _call_ros2_service(
            FavorGetWatchlist, "/favor/get_watchlist", req, timeout_sec=10.0
        )

        if not response.success:
            raise HTTPException(status_code=500, detail="获取自选股列表失败")

        return [
            WatchlistItemResponse(
                code=item.code,
                name=item.name,
                account_id=item.account_id or "default",
                group_name=item.group_name or "自选股",
                source_condition=item.source_condition,
                signal_type=item.signal_type,
                confidence=item.confidence,
                added_at=item.added_at or None,
            )
            for item in response.items
        ]
    except HTTPException:
        raise
    except TimeoutError as e:
        logger.error(f"获取自选股超时: {e}")
        raise HTTPException(status_code=504, detail=str(e))
    except Exception as e:
        logger.error(f"获取自选股列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/favor/watchlist", response_model=dict)
async def add_to_watchlist(request: WatchlistAddRequest):
    """添加单只股票到自选股（直接写入 DuckDB，不经过 ROS2）"""
    try:
        from lanbao_favor.duckdb_storage import FavorStorage

        storage = FavorStorage()
        try:
            success = storage.add_to_watchlist({
                "code": request.code,
                "name": request.name,
                "account_id": request.account_id,
                "group_name": request.group_name,
                "source_condition": request.source_condition,
                "signal_type": "",
                "confidence": 0.0,
                "added_at": datetime.now(),
            })
            if not success:
                raise HTTPException(status_code=500, detail="添加失败")
            return {"success": True, "code": request.code, "message": "已添加"}
        finally:
            storage.close()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"添加自选股失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/favor/watchlist/{code}")
async def remove_from_watchlist(
    code: str,
    account_id: str = Query("default"),
    group_name: str = Query("自选股"),
):
    """从自选股中移除指定股票（直接操作 DuckDB，不经过 ROS2）"""
    try:
        from lanbao_favor.duckdb_storage import FavorStorage

        storage = FavorStorage()
        try:
            success = storage.remove_from_watchlist(code, account_id, group_name)
            if not success:
                raise HTTPException(status_code=404, detail="股票不在自选股中")
            return {"success": True, "code": code, "message": "已移除"}
        finally:
            storage.close()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"移除自选股失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/favor/eastmoney/watchlist")
async def get_eastmoney_watchlist(group_name: str = Query("自选股")):
    """从东方财富平台获取自选股列表（含腾讯财经实时行情）"""
    try:
        from lanbao_favor.favor_sync_manager import FavorSyncManager
        sync_mgr = FavorSyncManager()
        stocks = sync_mgr.get_watchlist(group_name=group_name)

        # 获取腾讯财经实时行情
        codes = [s['code'] for s in stocks]
        quotes = _fetch_tx_quotes(codes)

        items = []
        for s in stocks:
            code = s['code']
            q = quotes.get(code, {})
            items.append({
                'code': code,
                'name': q.get('name', s.get('name', '')),
                'price': q.get('price', 0.0),
                'change': q.get('change', 0.0),
                'change_pct': q.get('change_pct', 0.0),
                'high': q.get('high', 0.0),
                'low': q.get('low', 0.0),
            })

        return {"items": items, "group_name": group_name}
    except ValueError:
        raise HTTPException(status_code=503, detail="EastMoney 凭证未配置，请在 .env 中设置 EASTMONEY_APPKEY 和 EASTMONEY_COOKIE")
    except Exception as e:
        logger.error(f"获取 EastMoney 自选股失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/favor/eastmoney/groups")
async def get_eastmoney_groups():
    """获取东方财富分组列表"""
    try:
        from lanbao_favor.favor_sync_manager import FavorSyncManager
        sync_mgr = FavorSyncManager()
        groups = sync_mgr.get_groups()
        return {"groups": groups}
    except ValueError:
        raise HTTPException(status_code=503, detail="EastMoney 凭证未配置")
    except Exception as e:
        logger.error(f"获取 EastMoney 分组失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/favor/eastmoney/sync")
async def sync_to_eastmoney(group_name: str = Query("自选股")):
    """将系统自选股同步到东方财富"""
    try:
        from lanbao_favor.duckdb_storage import FavorStorage
        from lanbao_favor.favor_sync_manager import FavorSyncManager

        storage = FavorStorage()
        try:
            items = storage.list_watchlist(group_name=group_name)
            codes = [item["code"] for item in items]
        finally:
            storage.close()

        if not codes:
            return {"success": True, "message": "无自选股需要同步", "synced": 0}

        sync_mgr = FavorSyncManager()
        success = sync_mgr.add_stocks(codes, group_name=group_name)

        return {
            "success": success,
            "message": "同步成功" if success else "同步失败",
            "synced": len(codes),
        }
    except ValueError:
        raise HTTPException(status_code=503, detail="EastMoney 凭证未配置")
    except Exception as e:
        logger.error(f"同步到 EastMoney 失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/favor/conditions", response_model=List[FavorConditionResponse])
async def list_conditions(enabled_only: bool = Query(False)):
    """获取选股条件列表"""
    try:
        from lanbao_interfaces.srv import FavorManageCondition

        req = FavorManageCondition.Request()
        req.operation = "list"
        req.condition_id = 0
        req.condition_json = ""

        response = _call_ros2_service(
            FavorManageCondition, "/favor/manage_condition", req, timeout_sec=10.0
        )

        if not response.success:
            raise HTTPException(status_code=500, detail="获取条件列表失败")

        import json
        conditions = json.loads(response.conditions_json)
        if enabled_only:
            conditions = [c for c in conditions if c.get("enabled", True)]

        return [
            FavorConditionResponse(
                id=c.get("id", 0),
                name=c["name"],
                query=c["query"],
                description=c.get("description", ""),
                enabled=c.get("enabled", True),
                priority=c.get("priority", 0),
                max_results=c.get("max_results", 15),
                filter_hot_sector=c.get("filter_hot_sector", False),
                filter_min_cap_yi=c.get("filter_min_cap_yi"),
                created_at=str(c.get("created_at", "")) if c.get("created_at") else None,
                updated_at=str(c.get("updated_at", "")) if c.get("updated_at") else None,
            )
            for c in conditions
        ]
    except HTTPException:
        raise
    except TimeoutError as e:
        logger.error(f"获取条件列表超时: {e}")
        raise HTTPException(status_code=504, detail=str(e))
    except Exception as e:
        logger.error(f"获取条件列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/favor/conditions", response_model=dict)
async def create_condition(request: FavorConditionCreate):
    """创建选股条件"""
    try:
        from lanbao_interfaces.srv import FavorManageCondition

        import json
        req = FavorManageCondition.Request()
        req.operation = "save"
        req.condition_id = 0
        req.condition_json = json.dumps(request.model_dump())

        response = _call_ros2_service(
            FavorManageCondition, "/favor/manage_condition", req, timeout_sec=10.0
        )

        if not response.success:
            raise HTTPException(status_code=500, detail=response.message or "保存失败")

        return {"success": True, "message": response.message}
    except HTTPException:
        raise
    except TimeoutError as e:
        logger.error(f"创建条件超时: {e}")
        raise HTTPException(status_code=504, detail=str(e))
    except Exception as e:
        logger.error(f"创建条件失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/favor/conditions/{condition_id}")
async def delete_condition(condition_id: int):
    """删除选股条件"""
    try:
        from lanbao_interfaces.srv import FavorManageCondition

        req = FavorManageCondition.Request()
        req.operation = "delete"
        req.condition_id = condition_id
        req.condition_json = ""

        response = _call_ros2_service(
            FavorManageCondition, "/favor/manage_condition", req, timeout_sec=10.0
        )

        if not response.success:
            raise HTTPException(status_code=404, detail=response.message or "条件不存在")

        return {"success": True, "condition_id": condition_id, "message": "已删除"}
    except HTTPException:
        raise
    except TimeoutError as e:
        logger.error(f"删除条件超时: {e}")
        raise HTTPException(status_code=504, detail=str(e))
    except Exception as e:
        logger.error(f"删除条件失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
