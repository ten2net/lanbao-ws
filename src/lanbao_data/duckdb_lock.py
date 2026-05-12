# 代理导入：将子包中的 db_lock 暴露到 lanbao_data 包根
from .lanbao_data.duckdb_lock import db_lock

__all__ = ["db_lock"]
