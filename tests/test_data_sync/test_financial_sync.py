import os
import sys
import pytest
from unittest.mock import Mock, patch
import pandas as pd
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src/lanbao_data'))

from lanbao_data.data_sync_node import DataSyncNode


class TestFinancialSyncLogic:
    @patch('lanbao_data.data_sync_node.TushareAdapter')
    @patch('lanbao_data.data_sync_node.LanBaoBaseNode.__init__', return_value=None)
    def test_generate_report_periods(self, mock_base_init, mock_adapter_cls):
        """测试报告期生成"""
        node = DataSyncNode.__new__(DataSyncNode)
        node._financial_start_period = '20200101'

        periods = node._generate_report_periods('20200101')

        assert '20200331' in periods
        assert '20201231' in periods
        # Current date is 2026-05-15, should include 2026Q1 (20260331) but not 2026Q2 (20260630)
        assert '20260331' in periods
        assert '20260630' not in periods

    @patch('lanbao_data.data_sync_node.TushareAdapter')
    @patch('lanbao_data.data_sync_node.LanBaoBaseNode.__init__', return_value=None)
    def test_build_financial_sync_tasks(self, mock_base_init, mock_adapter_cls):
        """测试同步任务构建：已有数据跳过，只生成缺失的任务"""
        node = DataSyncNode.__new__(DataSyncNode)
        node._financial_start_period = '20241201'

        stock_list = pd.DataFrame({'symbol': ['000001.SZ', '600519.SH']})

        mock_storage = Mock()
        mock_storage.get_existing_financial_periods.return_value = {
            '000001.SZ': {'20241231'},
        }

        with patch('lanbao_data.data_sync_node.DuckDBStorage', return_value=mock_storage):
            tasks = node._build_financial_sync_tasks(stock_list)

        symbols = [t['symbol'] for t in tasks]
        assert '600519.SH' in symbols
        # 000001.SZ already has 2024Q4, so no task for it
        assert not any(t['symbol'] == '000001.SZ' and t['period'] == '20241231' for t in tasks)

    @patch('lanbao_data.data_sync_node.TushareAdapter')
    @patch('lanbao_data.data_sync_node.LanBaoBaseNode.__init__', return_value=None)
    def test_build_tasks_empty_stock_list(self, mock_base_init, mock_adapter_cls):
        """测试空股票列表返回空任务"""
        node = DataSyncNode.__new__(DataSyncNode)
        node._financial_start_period = '20200101'

        stock_list = pd.DataFrame({'symbol': []})
        tasks = node._build_financial_sync_tasks(stock_list)
        assert tasks == []
