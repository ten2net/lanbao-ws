"""自选股模块 DuckDB 存储层"""
import os
from typing import List, Dict, Optional, Any
from datetime import datetime

import duckdb


class FavorStorage:
    """自选股数据存储"""

    def __init__(self, db_path: str = None):
        self._db_path = db_path or os.getenv('DUCKDB_PATH', './data/lanbao.duckdb')
        self._conn = duckdb.connect(self._db_path)

    def close(self):
        self._conn.close()

    def list_conditions(self, enabled_only: bool = False) -> List[Dict]:
        sql = "SELECT * FROM favor_conditions"
        if enabled_only:
            sql += " WHERE enabled = true"
        sql += " ORDER BY priority, id"
        result = self._conn.execute(sql).fetchall()
        columns = [desc[0] for desc in self._conn.description]
        return [dict(zip(columns, row)) for row in result]

    def get_condition(self, condition_id: int) -> Optional[Dict]:
        result = self._conn.execute(
            "SELECT * FROM favor_conditions WHERE id = ?", [condition_id]
        ).fetchone()
        if not result:
            return None
        columns = [desc[0] for desc in self._conn.description]
        return dict(zip(columns, result))

    def save_condition(self, condition: Dict) -> int:
        now = datetime.now()
        if condition.get('id'):
            self._conn.execute("""
                UPDATE favor_conditions
                SET name = ?, query = ?, description = ?, enabled = ?,
                    priority = ?, max_results = ?, filter_hot_sector = ?,
                    filter_min_cap_yi = ?, updated_at = ?
                WHERE id = ?
            """, [
                condition['name'], condition['query'], condition.get('description', ''),
                condition.get('enabled', True), condition.get('priority', 0),
                condition.get('max_results', 15), condition.get('filter_hot_sector', False),
                condition.get('filter_min_cap_yi'), now, condition['id']
            ])
            return condition['id']
        else:
            self._conn.execute("""
                INSERT INTO favor_conditions
                (name, query, description, enabled, priority, max_results,
                 filter_hot_sector, filter_min_cap_yi, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, [
                condition['name'], condition['query'], condition.get('description', ''),
                condition.get('enabled', True), condition.get('priority', 0),
                condition.get('max_results', 15), condition.get('filter_hot_sector', False),
                condition.get('filter_min_cap_yi'), now, now
            ])
            result = self._conn.execute(
                "SELECT id FROM favor_conditions WHERE name = ? AND query = ? ORDER BY id DESC LIMIT 1",
                [condition['name'], condition['query']]
            ).fetchone()
            return result[0] if result else 0

    def delete_condition(self, condition_id: int) -> bool:
        self._conn.execute("DELETE FROM favor_conditions WHERE id = ?", [condition_id])
        result = self._conn.execute("SELECT * FROM favor_conditions WHERE id = ?", [condition_id]).fetchone()
        return result is None

    def list_watchlist(self, account_id: str = None, group_name: str = None) -> List[Dict]:
        sql = "SELECT * FROM favor_watchlist WHERE 1=1"
        params = []
        if account_id:
            sql += " AND account_id = ?"
            params.append(account_id)
        if group_name:
            sql += " AND group_name = ?"
            params.append(group_name)
        sql += " ORDER BY added_at DESC"
        result = self._conn.execute(sql, params).fetchall()
        columns = [desc[0] for desc in self._conn.description]
        return [dict(zip(columns, row)) for row in result]

    def add_to_watchlist(self, item: Dict) -> bool:
        try:
            self._conn.execute("""
                INSERT OR REPLACE INTO favor_watchlist
                (code, name, account_id, group_name, source_condition,
                 signal_type, confidence, added_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, [
                item['code'], item.get('name', ''),
                item.get('account_id', 'default'),
                item.get('group_name', '自选股'),
                item.get('source_condition', ''),
                item.get('signal_type', ''),
                item.get('confidence', 0.0),
                item.get('added_at', datetime.now())
            ])
            return True
        except Exception:
            return False

    def remove_from_watchlist(self, code: str, account_id: str, group_name: str) -> bool:
        self._conn.execute(
            "DELETE FROM favor_watchlist WHERE code = ? AND account_id = ? AND group_name = ?",
            [code, account_id, group_name]
        )
        result = self._conn.execute(
            "SELECT * FROM favor_watchlist WHERE code = ? AND account_id = ? AND group_name = ?",
            [code, account_id, group_name]
        ).fetchone()
        return result is None

    def clear_watchlist(self, account_id: str = None, group_name: str = None) -> int:
        # Count before delete
        count_sql = "SELECT COUNT(*) FROM favor_watchlist WHERE 1=1"
        count_params = []
        if account_id:
            count_sql += " AND account_id = ?"
            count_params.append(account_id)
        if group_name:
            count_sql += " AND group_name = ?"
            count_params.append(group_name)
        before = self._conn.execute(count_sql, count_params).fetchone()[0]

        sql = "DELETE FROM favor_watchlist WHERE 1=1"
        params = []
        if account_id:
            sql += " AND account_id = ?"
            params.append(account_id)
        if group_name:
            sql += " AND group_name = ?"
            params.append(group_name)
        self._conn.execute(sql, params)
        return before

    def save_pick_log(self, log: Dict) -> int:
        self._conn.execute("""
            INSERT INTO favor_pick_logs
            (condition_id, condition_name, picked_count, filtered_count,
             duration_ms, picked_codes, error_message, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            log.get('condition_id'), log.get('condition_name'),
            log.get('picked_count', 0), log.get('filtered_count', 0),
            log.get('duration_ms', 0), log.get('picked_codes', []),
            log.get('error_message', ''), log.get('created_at', datetime.now())
        ])
        result = self._conn.execute(
            "SELECT id FROM favor_pick_logs WHERE condition_name = ? ORDER BY id DESC LIMIT 1",
            [log.get('condition_name', '')]
        ).fetchone()
        return result[0] if result else 0

    def list_pick_logs(self, limit: int = 50, offset: int = 0) -> List[Dict]:
        result = self._conn.execute(
            "SELECT * FROM favor_pick_logs ORDER BY created_at DESC LIMIT ? OFFSET ?",
            [limit, offset]
        ).fetchall()
        columns = [desc[0] for desc in self._conn.description]
        return [dict(zip(columns, row)) for row in result]
