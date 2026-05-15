"""自选股模块 DuckDB 存储层"""
import os
from pathlib import Path
from typing import List, Dict, Optional, Any
from datetime import datetime

import duckdb


class FavorStorage:
    """自选股数据存储（使用独立数据库文件，避免与其他节点冲突）"""

    def __init__(self, db_path: str = None, read_only: bool = False):
        self._db_path = db_path or os.getenv('FAVOR_DB_PATH', './data/favor.duckdb')
        self._read_only = read_only
        self._conn = None
        Path(self._db_path).parent.mkdir(parents=True, exist_ok=True)
        if not read_only:
            self._init_tables()

    def _ensure_conn(self):
        """懒加载连接：按需打开，避免启动时抢占锁"""
        if self._conn is None:
            self._conn = duckdb.connect(self._db_path, read_only=self._read_only)

    def close(self):
        if self._conn is not None:
            try:
                if not self._read_only:
                    self._conn.execute("CHECKPOINT")
            except Exception:
                pass
            self._conn.close()
            self._conn = None

    def _init_tables(self):
        """初始化自选股相关表结构"""
        self._ensure_conn()
        # favor_conditions
        self._conn.execute("CREATE SEQUENCE IF NOT EXISTS favor_condition_id_seq START 1;")
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS favor_conditions (
                id INTEGER PRIMARY KEY DEFAULT nextval('favor_condition_id_seq'),
                name VARCHAR NOT NULL,
                query VARCHAR NOT NULL,
                description VARCHAR,
                enabled BOOLEAN DEFAULT true,
                priority INTEGER DEFAULT 0,
                max_results INTEGER DEFAULT 15,
                filter_hot_sector BOOLEAN DEFAULT false,
                filter_min_cap_yi DOUBLE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # favor_accounts
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS favor_accounts (
                id VARCHAR PRIMARY KEY,
                name VARCHAR NOT NULL,
                env_prefix VARCHAR,
                target_group VARCHAR DEFAULT '自选股',
                enabled BOOLEAN DEFAULT true,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # favor_watchlist
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS favor_watchlist (
                code VARCHAR NOT NULL,
                name VARCHAR,
                account_id VARCHAR DEFAULT 'default',
                group_name VARCHAR DEFAULT '自选股',
                source_condition VARCHAR,
                signal_type VARCHAR,
                confidence DOUBLE,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (code, account_id, group_name)
            )
        """)

        # favor_pick_logs
        self._conn.execute("CREATE SEQUENCE IF NOT EXISTS favor_pick_log_id_seq START 1;")
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS favor_pick_logs (
                id INTEGER PRIMARY KEY DEFAULT nextval('favor_pick_log_id_seq'),
                condition_id INTEGER,
                condition_name VARCHAR,
                picked_count INTEGER,
                filtered_count INTEGER,
                duration_ms INTEGER,
                picked_codes VARCHAR[],
                error_message VARCHAR,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Insert default account
        self._conn.execute("""
            INSERT OR IGNORE INTO favor_accounts (id, name, target_group, enabled)
            VALUES ('default', '默认账户', '自选股', true)
        """)

    def list_conditions(self, enabled_only: bool = False) -> List[Dict]:
        self._ensure_conn()
        sql = "SELECT * FROM favor_conditions"
        if enabled_only:
            sql += " WHERE enabled = true"
        sql += " ORDER BY priority, id"
        result = self._conn.execute(sql).fetchall()
        columns = [desc[0] for desc in self._conn.description]
        return [dict(zip(columns, row)) for row in result]

    def get_condition(self, condition_id: int) -> Optional[Dict]:
        self._ensure_conn()
        result = self._conn.execute(
            "SELECT * FROM favor_conditions WHERE id = ?", [condition_id]
        ).fetchone()
        if not result:
            return None
        columns = [desc[0] for desc in self._conn.description]
        return dict(zip(columns, result))

    def save_condition(self, condition: Dict) -> int:
        self._ensure_conn()
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
        self._ensure_conn()
        self._conn.execute("DELETE FROM favor_conditions WHERE id = ?", [condition_id])
        result = self._conn.execute("SELECT * FROM favor_conditions WHERE id = ?", [condition_id]).fetchone()
        return result is None

    def list_watchlist(self, account_id: str = None, group_name: str = None) -> List[Dict]:
        self._ensure_conn()
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
        self._ensure_conn()
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
        self._ensure_conn()
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
        self._ensure_conn()
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
        self._ensure_conn()
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
        self._ensure_conn()
        result = self._conn.execute(
            "SELECT * FROM favor_pick_logs ORDER BY created_at DESC LIMIT ? OFFSET ?",
            [limit, offset]
        ).fetchall()
        columns = [desc[0] for desc in self._conn.description]
        return [dict(zip(columns, row)) for row in result]
