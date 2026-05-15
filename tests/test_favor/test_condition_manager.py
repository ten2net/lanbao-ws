"""Tests for lanbao_favor ConditionManager."""
import os
import tempfile

import duckdb
import pytest

from lanbao_favor.duckdb_storage import FavorStorage
from lanbao_favor.condition_manager import ConditionManager
from lanbao_favor.models import FavorCondition


@pytest.fixture
def manager():
    """Create a ConditionManager backed by a temporary DuckDB database."""
    fd, db_path = tempfile.mkstemp(suffix=".duckdb")
    os.close(fd)
    os.unlink(db_path)

    # Create tables directly so tests are self-contained
    conn = duckdb.connect(db_path)

    conn.execute("CREATE SEQUENCE favor_condition_id_seq START 1;")
    conn.execute("""
        CREATE TABLE favor_conditions (
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

    conn.execute("""
        CREATE TABLE favor_accounts (
            id VARCHAR PRIMARY KEY,
            name VARCHAR NOT NULL,
            env_prefix VARCHAR,
            target_group VARCHAR DEFAULT '自选股',
            enabled BOOLEAN DEFAULT true,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.execute("""
        CREATE TABLE favor_watchlist (
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

    conn.execute("CREATE SEQUENCE favor_pick_log_id_seq START 1;")
    conn.execute("""
        CREATE TABLE favor_pick_logs (
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

    conn.execute("""
        INSERT OR IGNORE INTO favor_accounts (id, name, target_group, enabled)
        VALUES ('default', '默认账户', '自选股', true)
    """)

    conn.close()

    storage = FavorStorage(db_path)
    mgr = ConditionManager(storage)
    yield mgr
    storage.close()
    os.unlink(db_path)


class TestConditionManager:
    def test_list_empty(self, manager: ConditionManager):
        conditions = manager.list_conditions()
        assert conditions == []

    def test_save_and_get(self, manager: ConditionManager):
        condition = FavorCondition(
            name="High Volume",
            query="volume > 1000000",
            description="Test condition",
            enabled=True,
            priority=1,
            max_results=10,
            filter_hot_sector=False,
        )
        cid = manager.save_condition(condition)
        assert cid > 0

        fetched = manager.get_condition(cid)
        assert fetched is not None
        assert fetched.name == "High Volume"
        assert fetched.query == "volume > 1000000"
        assert fetched.description == "Test condition"
        assert fetched.enabled is True
        assert fetched.priority == 1
        assert fetched.max_results == 10
        assert fetched.filter_hot_sector is False

    def test_list_enabled_only(self, manager: ConditionManager):
        manager.save_condition(FavorCondition(name="Enabled", query="q1", enabled=True))
        manager.save_condition(FavorCondition(name="Disabled", query="q2", enabled=False))

        all_conds = manager.list_conditions()
        assert len(all_conds) == 2

        enabled_conds = manager.list_conditions(enabled_only=True)
        assert len(enabled_conds) == 1
        assert enabled_conds[0].name == "Enabled"

    def test_delete(self, manager: ConditionManager):
        condition = FavorCondition(name="ToDelete", query="q")
        cid = manager.save_condition(condition)

        assert manager.delete_condition(cid) is True
        assert manager.get_condition(cid) is None
