"""Tests for lanbao_favor DuckDB storage layer."""
import os
import tempfile
from datetime import datetime

import duckdb
import pytest

from lanbao_favor.duckdb_storage import FavorStorage


@pytest.fixture
def storage():
    """Create a FavorStorage backed by a temporary DuckDB database."""
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

    fs = FavorStorage(db_path)
    yield fs
    fs.close()
    os.unlink(db_path)


class TestConditionCrud:
    def test_create_and_list_conditions(self, storage: FavorStorage):
        cond = {
            "name": "High Volume",
            "query": "volume > 1000000",
            "description": "Test condition",
            "enabled": True,
            "priority": 1,
            "max_results": 10,
            "filter_hot_sector": False,
        }
        cid = storage.save_condition(cond)
        assert cid > 0

        conditions = storage.list_conditions()
        assert len(conditions) == 1
        assert conditions[0]["name"] == "High Volume"
        assert conditions[0]["query"] == "volume > 1000000"

    def test_get_condition(self, storage: FavorStorage):
        cond = {"name": "MA Cross", "query": "ma5 > ma10"}
        cid = storage.save_condition(cond)

        fetched = storage.get_condition(cid)
        assert fetched is not None
        assert fetched["name"] == "MA Cross"

    def test_get_condition_not_found(self, storage: FavorStorage):
        assert storage.get_condition(9999) is None

    def test_update_condition(self, storage: FavorStorage):
        cond = {"name": "Old Name", "query": "q1"}
        cid = storage.save_condition(cond)

        updated = {
            "id": cid,
            "name": "New Name",
            "query": "q2",
            "description": "Updated",
            "enabled": False,
            "priority": 5,
            "max_results": 20,
            "filter_hot_sector": True,
            "filter_min_cap_yi": 50.0,
        }
        returned_id = storage.save_condition(updated)
        assert returned_id == cid

        fetched = storage.get_condition(cid)
        assert fetched["name"] == "New Name"
        assert fetched["enabled"] is False
        assert fetched["priority"] == 5
        assert fetched["filter_min_cap_yi"] == 50.0

    def test_delete_condition(self, storage: FavorStorage):
        cond = {"name": "ToDelete", "query": "q"}
        cid = storage.save_condition(cond)
        assert storage.delete_condition(cid) is True
        assert storage.get_condition(cid) is None

    def test_list_enabled_only(self, storage: FavorStorage):
        storage.save_condition({"name": "Enabled", "query": "q1", "enabled": True})
        storage.save_condition({"name": "Disabled", "query": "q2", "enabled": False})

        all_conds = storage.list_conditions()
        assert len(all_conds) == 2

        enabled_conds = storage.list_conditions(enabled_only=True)
        assert len(enabled_conds) == 1
        assert enabled_conds[0]["name"] == "Enabled"


class TestWatchlistCrud:
    def test_add_and_list_watchlist(self, storage: FavorStorage):
        item = {
            "code": "000001.SZ",
            "name": "平安银行",
            "account_id": "default",
            "group_name": "自选股",
            "source_condition": "High Volume",
            "signal_type": "BUY",
            "confidence": 0.85,
        }
        assert storage.add_to_watchlist(item) is True

        items = storage.list_watchlist()
        assert len(items) == 1
        assert items[0]["code"] == "000001.SZ"
        assert items[0]["confidence"] == 0.85

    def test_list_watchlist_filtered(self, storage: FavorStorage):
        storage.add_to_watchlist({"code": "A", "account_id": "acc1", "group_name": "g1"})
        storage.add_to_watchlist({"code": "B", "account_id": "acc1", "group_name": "g2"})
        storage.add_to_watchlist({"code": "C", "account_id": "acc2", "group_name": "g1"})

        assert len(storage.list_watchlist(account_id="acc1")) == 2
        assert len(storage.list_watchlist(group_name="g1")) == 2
        assert len(storage.list_watchlist(account_id="acc1", group_name="g2")) == 1

    def test_remove_from_watchlist(self, storage: FavorStorage):
        storage.add_to_watchlist({"code": "X", "account_id": "a", "group_name": "g"})
        assert storage.remove_from_watchlist("X", "a", "g") is True
        assert len(storage.list_watchlist()) == 0

    def test_clear_watchlist(self, storage: FavorStorage):
        storage.add_to_watchlist({"code": "A", "account_id": "a1", "group_name": "g1"})
        storage.add_to_watchlist({"code": "B", "account_id": "a1", "group_name": "g2"})
        storage.add_to_watchlist({"code": "C", "account_id": "a2", "group_name": "g1"})

        cleared = storage.clear_watchlist(account_id="a1")
        assert cleared == 2
        assert len(storage.list_watchlist()) == 1

    def test_add_duplicate_replaces(self, storage: FavorStorage):
        storage.add_to_watchlist({"code": "D", "name": "First", "account_id": "a", "group_name": "g"})
        storage.add_to_watchlist({"code": "D", "name": "Second", "account_id": "a", "group_name": "g"})

        items = storage.list_watchlist()
        assert len(items) == 1
        assert items[0]["name"] == "Second"


class TestPickLog:
    def test_save_and_list_pick_logs(self, storage: FavorStorage):
        log = {
            "condition_id": 1,
            "condition_name": "Test",
            "picked_count": 5,
            "filtered_count": 2,
            "duration_ms": 120,
            "picked_codes": ["000001.SZ", "000002.SZ"],
            "error_message": "",
        }
        lid = storage.save_pick_log(log)
        assert lid > 0

        logs = storage.list_pick_logs()
        assert len(logs) == 1
        assert logs[0]["condition_name"] == "Test"
        assert logs[0]["picked_codes"] == ["000001.SZ", "000002.SZ"]

    def test_list_pick_logs_pagination(self, storage: FavorStorage):
        for i in range(5):
            storage.save_pick_log({"condition_name": f"Log{i}"})

        page = storage.list_pick_logs(limit=2, offset=0)
        assert len(page) == 2

        page2 = storage.list_pick_logs(limit=2, offset=2)
        assert len(page2) == 2
        assert page[0]["condition_name"] != page2[0]["condition_name"]
