"""Tests for lanbao_favor StockPicker."""
import sys
from unittest.mock import Mock, patch, MagicMock

import pytest

from lanbao_favor.models import FavorCondition
from lanbao_favor.stock_picker import StockPicker, StockInfo


class MockStock:
    """Mock stock object returned by StockSelector."""

    def __init__(self, code, name, market_type=""):
        self.code = code
        self.name = name
        self.market_type = market_type


class MockSelectResult:
    """Mock result object returned by StockSelector.select()."""

    def __init__(self, stocks):
        self.stocks = stocks


def _make_picker(mock_selector):
    """Create a StockPicker with a pre-injected mock selector."""
    picker = object.__new__(StockPicker)
    picker._selector = mock_selector
    picker._hot_sector_codes = None
    return picker


class TestStockPicker:
    def test_pick_mocked(self):
        """Verify basic pick flow with mocked stock-select."""
        mock_selector = Mock()
        mock_stocks = [
            MockStock("000001.SZ", "平安银行", "A股"),
            MockStock("600000.SH", "浦发银行", "A股"),
        ]
        mock_selector.select.return_value = MockSelectResult(mock_stocks)

        picker = _make_picker(mock_selector)
        condition = FavorCondition(
            name="Test Pick",
            query="银行板块",
            max_results=10,
        )

        result = picker.pick(condition)

        assert len(result) == 2
        assert result[0].code == "000001.SZ"
        assert result[0].name == "平安银行"
        assert result[0].market_type == "A股"
        assert result[0].source_condition == "Test Pick"
        assert result[1].code == "600000.SH"

        mock_selector.select.assert_called_once_with("银行板块", max_results=10)

    def test_pick_empty_result(self):
        """Verify pick handles empty result gracefully."""
        mock_selector = Mock()
        mock_selector.select.return_value = MockSelectResult([])

        picker = _make_picker(mock_selector)
        condition = FavorCondition(name="Empty", query="no_match")
        result = picker.pick(condition)

        assert result == []

    def test_pick_selector_exception(self):
        """Verify pick returns empty list when selector raises."""
        mock_selector = Mock()
        mock_selector.select.side_effect = Exception("API error")

        picker = _make_picker(mock_selector)
        condition = FavorCondition(name="Error", query="fail")
        result = picker.pick(condition)

        assert result == []

    def test_filter_by_hot_sectors_empty(self):
        """Verify fallback when sector data fails."""
        mock_selector = Mock()
        mock_stocks = [
            MockStock("000001.SZ", "平安银行"),
            MockStock("600000.SH", "浦发银行"),
        ]
        mock_selector.select.return_value = MockSelectResult(mock_stocks)

        picker = _make_picker(mock_selector)
        condition = FavorCondition(
            name="Hot Sector",
            query="热门板块",
            filter_hot_sector=True,
        )

        # Simulate import failure for SectorRotationTracker
        def _fail_import(*args, **kwargs):
            raise ImportError("No module named 'strategies'")

        with patch("builtins.__import__", side_effect=_fail_import):
            result = picker.pick(condition)

        # Should fallback to returning all stocks
        assert len(result) == 2

    def test_pick_multiple(self):
        """Verify batch picking."""
        mock_selector = Mock()
        mock_selector.select.side_effect = [
            MockSelectResult([MockStock("000001.SZ", "平安银行")]),
            MockSelectResult([MockStock("600000.SH", "浦发银行")]),
        ]

        picker = _make_picker(mock_selector)
        conditions = [
            FavorCondition(name="Banks", query="银行"),
            FavorCondition(name="Insurance", query="保险"),
        ]

        results = picker.pick_multiple(conditions)

        assert len(results) == 2
        assert "Banks" in results
        assert "Insurance" in results
        assert len(results["Banks"]) == 1
        assert len(results["Insurance"]) == 1
        assert results["Banks"][0].code == "000001.SZ"
        assert results["Insurance"][0].code == "600000.SH"
        assert results["Banks"][0].source_condition == "Banks"
        assert results["Insurance"][0].source_condition == "Insurance"

        assert mock_selector.select.call_count == 2

    def test_filter_by_market_cap_no_creds(self):
        """Verify market cap filter skipped when credentials missing."""
        mock_selector = Mock()
        mock_stocks = [
            MockStock("000001.SZ", "平安银行"),
        ]
        mock_selector.select.return_value = MockSelectResult(mock_stocks)

        picker = _make_picker(mock_selector)
        condition = FavorCondition(
            name="Cap Filter",
            query="大盘股",
            filter_min_cap_yi=100.0,
        )

        with patch.dict("os.environ", {}, clear=True):
            result = picker.pick(condition)

        # Should return stock without filtering since no env vars
        assert len(result) == 1
        assert result[0].code == "000001.SZ"

    def test_filter_by_market_cap_with_api(self):
        """Verify market cap filtering works with mocked EastMoneyAPI."""
        mock_selector = Mock()
        mock_stocks = [
            MockStock("000001.SZ", "平安银行"),
            MockStock("000002.SZ", "万科A"),
        ]
        mock_selector.select.return_value = MockSelectResult(mock_stocks)

        picker = _make_picker(mock_selector)
        condition = FavorCondition(
            name="Cap Filter",
            query="大盘股",
            filter_min_cap_yi=200.0,
        )

        mock_quote_large = Mock()
        mock_quote_large.code = "000001.SZ"
        mock_quote_large.circulating_cap = 500.0

        mock_quote_small = Mock()
        mock_quote_small.code = "000002.SZ"
        mock_quote_small.circulating_cap = 50.0

        mock_api = Mock()
        mock_api.get_batch_quotes.return_value = [mock_quote_large, mock_quote_small]

        mock_eastmoney_module = MagicMock()
        mock_eastmoney_module.EastMoneyAPI.return_value = mock_api

        env_vars = {"EASTMONEY_APPKEY": "test_key", "EASTMONEY_COOKIE": "test_cookie"}

        def _mock_import(name, *args, **kwargs):
            if name == "eastmoney_mcp.api":
                return mock_eastmoney_module
            return __builtins__["__import__"](name, *args, **kwargs)

        with patch.dict("os.environ", env_vars, clear=True):
            with patch("builtins.__import__", side_effect=_mock_import):
                result = picker.pick(condition)

        # Only the large cap stock should remain
        assert len(result) == 1
        assert result[0].code == "000001.SZ"
