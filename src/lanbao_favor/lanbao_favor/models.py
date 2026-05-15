"""Pydantic 模型定义"""
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel


class FavorCondition(BaseModel):
    id: Optional[int] = None
    name: str
    query: str
    description: str = ""
    enabled: bool = True
    priority: int = 0
    max_results: int = 15
    filter_hot_sector: bool = False
    filter_min_cap_yi: Optional[float] = None


class WatchlistItem(BaseModel):
    code: str
    name: str = ""
    account_id: str = "default"
    group_name: str = "自选股"
    source_condition: str = ""
    signal_type: str = ""
    confidence: float = 0.0


class PickResult(BaseModel):
    condition_name: str
    stocks: List[dict]
    count: int
