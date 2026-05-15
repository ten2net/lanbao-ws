"""选股条件管理器"""
from typing import List, Optional
from loguru import logger

from .models import FavorCondition
from .duckdb_storage import FavorStorage


class ConditionManager:
    """管理选股条件的 CRUD"""

    def __init__(self, storage: FavorStorage):
        self._storage = storage

    def list_conditions(self, enabled_only: bool = False) -> List[FavorCondition]:
        rows = self._storage.list_conditions(enabled_only=enabled_only)
        return [FavorCondition(**row) for row in rows]

    def get_condition(self, condition_id: int) -> Optional[FavorCondition]:
        row = self._storage.get_condition(condition_id)
        return FavorCondition(**row) if row else None

    def save_condition(self, condition: FavorCondition) -> int:
        cid = self._storage.save_condition(condition.model_dump(exclude_none=True))
        logger.info(f"条件已保存: {condition.name} (id={cid})")
        return cid

    def delete_condition(self, condition_id: int) -> bool:
        success = self._storage.delete_condition(condition_id)
        if success:
            logger.info(f"条件已删除: id={condition_id}")
        return success

    def get_enabled_conditions(self) -> List[FavorCondition]:
        return self.list_conditions(enabled_only=True)
