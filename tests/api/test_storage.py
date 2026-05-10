"""测试 JSON 存储服务"""
import pytest
import tempfile
from pathlib import Path

from lanbao_backtest.api.services.storage import BacktestStorage


@pytest.fixture
def temp_storage(monkeypatch):
    """使用临时目录的存储实例"""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = BacktestStorage()
        storage._reports_dir = Path(tmpdir)
        yield storage


def test_save_and_get_backtest(temp_storage):
    data = {"backtest_id": "bt_test_001", "meta": {"strategy_id": "ma_cross"}}
    temp_storage.save_backtest("bt_test_001", data)

    result = temp_storage.get_backtest("bt_test_001")
    assert result is not None
    assert result["backtest_id"] == "bt_test_001"


def test_get_nonexistent_backtest(temp_storage):
    assert temp_storage.get_backtest("bt_nonexistent") is None


def test_list_backtests(temp_storage):
    temp_storage.save_backtest("bt_002", {"backtest_id": "bt_002"})
    temp_storage.save_backtest("bt_001", {"backtest_id": "bt_001"})

    results = temp_storage.list_backtests()
    assert len(results) == 2
    # 按修改时间倒序
    assert results[0]["backtest_id"] == "bt_002"


def test_list_skips_secondary_files(temp_storage):
    """附属文件（如 .equity.json）不应出现在列表中"""
    temp_storage.save_backtest("bt_main", {"backtest_id": "bt_main"})

    # 创建一个附属文件
    equity_path = temp_storage._reports_dir / "bt_main.equity.json"
    equity_path.write_text('{"backtest_id": "bt_main", "series": []}')

    results = temp_storage.list_backtests()
    assert len(results) == 1
    assert results[0]["backtest_id"] == "bt_main"


def test_delete_backtest(temp_storage):
    temp_storage.save_backtest("bt_del", {"backtest_id": "bt_del"})
    # 创建附属文件
    equity_path = temp_storage._reports_dir / "bt_del.equity.json"
    equity_path.write_text('{"series": []}')

    assert temp_storage.delete_backtest("bt_del") is True
    assert temp_storage.get_backtest("bt_del") is None
    assert not equity_path.exists()


def test_update_tags(temp_storage):
    temp_storage.save_backtest("bt_tags", {"backtest_id": "bt_tags", "meta": {}})
    assert temp_storage.update_tags("bt_tags", ["优化", "验证"]) is True

    result = temp_storage.get_backtest("bt_tags")
    assert result["meta"]["tags"] == ["优化", "验证"]


def test_get_equity(temp_storage):
    equity_data = {"backtest_id": "bt_eq", "series": [{"date": "2024-01-01", "equity": 100000}]}
    equity_path = temp_storage._reports_dir / "bt_eq.equity.json"
    equity_path.write_text(str(equity_data).replace("'", '"'))

    result = temp_storage.get_equity("bt_eq")
    assert result is not None
    assert len(result) == 1
    assert result[0]["equity"] == 100000


def test_get_trades(temp_storage):
    trades_data = {"backtest_id": "bt_tr", "trades": [{"trade_id": "t1", "action": "BUY"}]}
    trades_path = temp_storage._reports_dir / "bt_tr.trades.json"
    trades_path.write_text(str(trades_data).replace("'", '"'))

    result = temp_storage.get_trades("bt_tr")
    assert result is not None
    assert len(result) == 1
    assert result[0]["action"] == "BUY"
