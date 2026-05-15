import os
import sys
import pytest
from unittest.mock import Mock, patch
import pandas as pd
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../src/lanbao_data"))

from lanbao_data.data_sync_node import DataSyncNode


class TestFinancialSyncLogic:
    @patch("lanbao_data.data_sync_node.TushareAdapter")
    @patch("lanbao_data.data_sync_node.LanBaoBaseNode.__init__", return_value=None)
    def test_generate_report_periods(self, mock_base_init, mock_adapter_cls):
        """测试报告期生成"""
        node = DataSyncNode.__new__(DataSyncNode)
        node._financial_start_period = "20200101"

        periods = node._generate_report_periods("20200101")

        assert "20200331" in periods
        assert "20201231" in periods
        # Current date is 2026-05-15, should include 2026Q1 (20260331) but not 2026Q2 (20260630)
        assert "20260331" in periods
        assert "20260630" not in periods

    @patch("lanbao_data.data_sync_node.TushareAdapter")
    @patch("lanbao_data.data_sync_node.LanBaoBaseNode.__init__", return_value=None)
    def test_build_financial_sync_tasks(self, mock_base_init, mock_adapter_cls):
        """测试同步任务构建：已有数据跳过，只生成缺失的任务"""
        node = DataSyncNode.__new__(DataSyncNode)
        node._financial_start_period = "20241201"

        stock_list = pd.DataFrame({"symbol": ["000001.SZ", "600519.SH"]})

        mock_storage = Mock()
        mock_storage.get_existing_financial_periods.return_value = {
            "000001.SZ": {"20241231"},
        }

        with patch("lanbao_data.data_sync_node.DuckDBStorage", return_value=mock_storage):
            tasks = node._build_financial_sync_tasks(stock_list)

        symbols = [t["symbol"] for t in tasks]
        assert "600519.SH" in symbols
        # 000001.SZ already has 2024Q4, so no task for it
        assert not any(t["symbol"] == "000001.SZ" and t["period"] == "20241231" for t in tasks)

    @patch("lanbao_data.data_sync_node.TushareAdapter")
    @patch("lanbao_data.data_sync_node.LanBaoBaseNode.__init__", return_value=None)
    def test_build_tasks_empty_stock_list(self, mock_base_init, mock_adapter_cls):
        """测试空股票列表返回空任务"""
        node = DataSyncNode.__new__(DataSyncNode)
        node._financial_start_period = "20200101"

        stock_list = pd.DataFrame({"symbol": []})
        tasks = node._build_financial_sync_tasks(stock_list)
        assert tasks == []

    @patch("lanbao_data.data_sync_node.TushareAdapter")
    @patch("lanbao_data.data_sync_node.LanBaoBaseNode.__init__", return_value=None)
    def test_should_sync_financial_today(self, mock_base_init, mock_adapter_cls):
        """测试周日判断逻辑"""
        import threading

        node = DataSyncNode.__new__(DataSyncNode)
        node._financial_sync_enabled = True
        node._financial_sync_running = False
        node._financial_sync_lock = threading.Lock()
        node._financial_sync_day = "sun"
        node._financial_sync_time = "02:00"
        node._last_financial_sync_time = None

        # Sunday at 3 AM
        with patch("lanbao_data.data_sync_node.datetime") as mock_dt:
            mock_now = Mock()
            mock_now.strftime.side_effect = ["03:00", "sun"]  # time, weekday
            mock_now.date.return_value = datetime(2026, 5, 10).date()
            mock_dt.now.return_value = mock_now

            assert node._should_sync_financial_today()

    @patch("lanbao_data.data_sync_node.TushareAdapter")
    @patch("lanbao_data.data_sync_node.LanBaoBaseNode.__init__", return_value=None)
    def test_should_not_sync_wrong_day(self, mock_base_init, mock_adapter_cls):
        """测试非配置日不触发"""
        import threading

        node = DataSyncNode.__new__(DataSyncNode)
        node._financial_sync_enabled = True
        node._financial_sync_running = False
        node._financial_sync_lock = threading.Lock()
        node._financial_sync_day = "sun"
        node._financial_sync_time = "02:00"
        node._last_financial_sync_time = None

        # Monday at 3 AM
        with patch("lanbao_data.data_sync_node.datetime") as mock_dt:
            mock_now = Mock()
            mock_now.strftime.side_effect = ["03:00", "mon"]
            mock_now.date.return_value = datetime(2026, 5, 11).date()
            mock_dt.now.return_value = mock_now

            assert not node._should_sync_financial_today()

    @patch("lanbao_data.data_sync_node.TushareAdapter")
    @patch("lanbao_data.data_sync_node.LanBaoBaseNode.__init__", return_value=None)
    def test_trigger_financial_sync_prevents_duplicate(self, mock_base_init, mock_adapter_cls):
        """测试重复触发被阻止"""
        import threading

        node = DataSyncNode.__new__(DataSyncNode)
        node._financial_sync_running = True
        node._financial_sync_lock = threading.Lock()

        node._trigger_financial_sync()
        assert node._financial_sync_running  # Still running, not changed

    @patch("lanbao_data.data_sync_node.TushareAdapter")
    @patch("lanbao_data.data_sync_node.LanBaoBaseNode.__init__", return_value=None)
    def test_sync_financial_job_resets_running_flag(self, mock_base_init, mock_adapter_cls):
        """测试同步任务完成后重置 running 标志"""
        import threading

        node = DataSyncNode.__new__(DataSyncNode)
        node._financial_sync_running = True
        node._financial_sync_lock = threading.Lock()
        node._financial_sync_stats = {}
        node._status = Mock()

        # Mock empty stock list (early return path)
        node._adapter = Mock()
        node._adapter.get_stock_list.return_value = pd.DataFrame({"symbol": []})

        node._sync_financial_job()

        assert not node._financial_sync_running

    @patch("lanbao_data.data_sync_node.TushareAdapter")
    @patch("lanbao_data.data_sync_node.LanBaoBaseNode.__init__", return_value=None)
    def test_partial_statement_failure_handled(self, mock_base_init, mock_adapter_cls):
        """测试部分报表缺失时标记为失败但不中断"""
        import threading

        node = DataSyncNode.__new__(DataSyncNode)
        node._financial_sync_running = True
        node._financial_sync_lock = threading.Lock()
        node._financial_batch_interval = 100
        node._financial_sync_stats = {}
        node._status = Mock()
        node._publish_alert = Mock()

        # Mock adapter to return only 2 of 3 statements
        node._adapter = Mock()
        node._adapter.get_stock_list.return_value = pd.DataFrame({"symbol": ["000001.SZ"]})
        node._adapter.get_balance_sheet.return_value = pd.DataFrame({"total_assets": [1.0]})
        node._adapter.get_income_statement.return_value = pd.DataFrame({"revenue": [1.0]})
        node._adapter.get_cashflow_statement.return_value = pd.DataFrame()  # empty

        # Mock storage
        mock_storage = Mock()
        mock_storage.save_balance_sheet.return_value = True
        mock_storage.save_income_statement.return_value = True
        mock_storage.save_cashflow_statement.return_value = False

        with patch("lanbao_data.data_sync_node.DuckDBStorage", return_value=mock_storage):
            node._sync_financial_job()

        # Should complete without exception, running flag reset
        assert not node._financial_sync_running
