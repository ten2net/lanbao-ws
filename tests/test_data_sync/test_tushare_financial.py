import os
import sys
import pytest
from unittest.mock import Mock, patch
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../src/lanbao_data"))

from lanbao_data.tushare_adapter import TushareAdapter


class TestTushareAdapterFinancial:
    @patch("lanbao_data.tushare_adapter.ts.pro_api")
    def test_get_balance_sheet(self, mock_pro_api):
        mock_pro = Mock()
        mock_pro_api.return_value = mock_pro
        mock_df = pd.DataFrame(
            {
                "ts_code": ["000001.SZ"],
                "ann_date": ["20250124"],
                "end_date": ["20241231"],
                "total_assets": [5000000000.0],
                "total_liab": [3000000000.0],
                "total_hldr_eqy_exc_min_int": [2000000000.0],
                "extra_field": [123.0],
            }
        )
        mock_pro.balancesheet.return_value = mock_df

        adapter = TushareAdapter(api_token="test_token")
        result = adapter.get_balance_sheet("000001.SZ", period="20241231")

        assert not result.empty
        assert result.iloc[0]["total_assets"] == 5000000000.0
        mock_pro.balancesheet.assert_called_once_with(ts_code="000001.SZ", period="20241231")

    @patch("lanbao_data.tushare_adapter.ts.pro_api")
    def test_get_income_statement(self, mock_pro_api):
        mock_pro = Mock()
        mock_pro_api.return_value = mock_pro
        mock_df = pd.DataFrame(
            {
                "ts_code": ["000001.SZ"],
                "ann_date": ["20250124"],
                "end_date": ["20241231"],
                "revenue": [1000000000.0],
                "operate_profit": [200000000.0],
                "net_income": [150000000.0],
            }
        )
        mock_pro.income.return_value = mock_df

        adapter = TushareAdapter(api_token="test_token")
        result = adapter.get_income_statement("000001.SZ", period="20241231")
        assert not result.empty
        assert result.iloc[0]["revenue"] == 1000000000.0

    @patch("lanbao_data.tushare_adapter.ts.pro_api")
    def test_get_cashflow_statement(self, mock_pro_api):
        mock_pro = Mock()
        mock_pro_api.return_value = mock_pro
        mock_df = pd.DataFrame(
            {
                "ts_code": ["000001.SZ"],
                "ann_date": ["20250124"],
                "end_date": ["20241231"],
                "n_cashflow_act": [100000000.0],
                "n_cashflow_inv_act": [-50000000.0],
                "f_cashflow_act": [-20000000.0],
            }
        )
        mock_pro.cashflow.return_value = mock_df

        adapter = TushareAdapter(api_token="test_token")
        result = adapter.get_cashflow_statement("000001.SZ", period="20241231")
        assert not result.empty
        assert result.iloc[0]["n_cashflow_act"] == 100000000.0

    @patch("lanbao_data.tushare_adapter.time")
    @patch("lanbao_data.tushare_adapter.ts.pro_api")
    def test_financial_rate_limit(self, mock_pro_api, mock_time):
        mock_pro = Mock()
        mock_pro_api.return_value = mock_pro
        mock_pro.balancesheet.return_value = pd.DataFrame(
            {
                "ts_code": ["000001.SZ"],
                "end_date": ["20241231"],
                "total_assets": [1.0],
            }
        )

        # Mock time to avoid real sleep
        mock_time.time.side_effect = [
            0.0,
            0.0,
            0.8,
            0.8,
        ]  # before, before, after 0.75s, after 0.75s
        mock_time.sleep = Mock()

        adapter = TushareAdapter(api_token="test_token")
        adapter.get_balance_sheet("000001.SZ", period="20241231")
        adapter.get_balance_sheet("000001.SZ", period="20240930")

        # Verify sleep was called with at least 0.75s
        sleep_calls = mock_time.sleep.call_args_list
        assert any(
            call[0][0] >= 0.75 for call in sleep_calls
        ), f"Expected sleep >= 0.75s, got {[call[0][0] for call in sleep_calls]}"

    @patch("lanbao_data.tushare_adapter.time")
    @patch("lanbao_data.tushare_adapter.ts.pro_api")
    def test_daily_rate_limit_unchanged(self, mock_pro_api, mock_time):
        mock_pro = Mock()
        mock_pro_api.return_value = mock_pro
        mock_pro.daily.return_value = pd.DataFrame(
            {
                "ts_code": ["000001.SZ"],
                "trade_date": ["20250124"],
                "open": [10.0],
            }
        )

        mock_time.time.side_effect = [0.0, 0.0, 0.15, 0.15]
        mock_time.sleep = Mock()

        adapter = TushareAdapter(api_token="test_token")
        adapter.get_daily_data("000001.SZ", "20250124", "20250124")
        adapter.get_daily_data("000001.SZ", "20250123", "20250123")

        # Verify sleep was called with 0.1s (not 0.75s)
        sleep_calls = mock_time.sleep.call_args_list
        assert all(
            call[0][0] <= 0.2 for call in sleep_calls
        ), f"Daily calls should use 0.1s interval, got {[call[0][0] for call in sleep_calls]}"

    @patch("lanbao_data.tushare_adapter.ts.pro_api")
    def test_empty_response_returns_empty_df(self, mock_pro_api):
        mock_pro = Mock()
        mock_pro_api.return_value = mock_pro
        mock_pro.balancesheet.return_value = pd.DataFrame()
        adapter = TushareAdapter(api_token="test_token")
        result = adapter.get_balance_sheet("000001.SZ", period="20241231")
        assert result.empty

    @patch("lanbao_data.tushare_adapter.ts.pro_api")
    def test_empty_income_returns_empty_df(self, mock_pro_api):
        mock_pro = Mock()
        mock_pro_api.return_value = mock_pro
        mock_pro.income.return_value = pd.DataFrame()
        adapter = TushareAdapter(api_token="test_token")
        assert adapter.get_income_statement("000001.SZ", period="20241231").empty

    @patch("lanbao_data.tushare_adapter.ts.pro_api")
    def test_empty_cashflow_returns_empty_df(self, mock_pro_api):
        mock_pro = Mock()
        mock_pro_api.return_value = mock_pro
        mock_pro.cashflow.return_value = pd.DataFrame()
        adapter = TushareAdapter(api_token="test_token")
        assert adapter.get_cashflow_statement("000001.SZ", period="20241231").empty
