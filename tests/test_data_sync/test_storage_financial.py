import os
import sys
import tempfile
import pytest
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src/lanbao_data'))

from lanbao_data.duckdb_storage import DuckDBStorage


class TestDuckDBStorageFinancial:
    @pytest.fixture
    def storage(self):
        fd, db_path = tempfile.mkstemp(suffix='.duckdb')
        os.close(fd)
        os.unlink(db_path)
        storage = DuckDBStorage(db_path, read_only=False)
        yield storage
        storage.close()
        if os.path.exists(db_path):
            os.unlink(db_path)

    def test_balance_sheet_crud(self, storage):
        df = pd.DataFrame({
            'ts_code': ['000001.SZ'],
            'ann_date': ['20250124'],
            'end_date': ['20241231'],
            'total_assets': [5000000000.0],
            'total_liab': [3000000000.0],
            'total_hldr_eqy_exc_min_int': [2000000000.0],
            'extra_col': [999.0],
        })
        assert storage.save_balance_sheet('000001.SZ', '20241231', df)
        result = storage.get_balance_sheet('000001.SZ')
        assert len(result) == 1
        assert result.iloc[0]['total_assets'] == 5000000000.0
        assert result.iloc[0]['report_period'] == '20241231'

    def test_income_statement_crud(self, storage):
        df = pd.DataFrame({
            'ts_code': ['000001.SZ'],
            'ann_date': ['20250124'],
            'end_date': ['20241231'],
            'revenue': [1000000000.0],
            'operate_profit': [200000000.0],
            'net_income': [150000000.0],
        })
        assert storage.save_income_statement('000001.SZ', '20241231', df)
        result = storage.get_income_statement('000001.SZ', period='20241231')
        assert len(result) == 1
        assert result.iloc[0]['revenue'] == 1000000000.0

    def test_cashflow_statement_crud(self, storage):
        df = pd.DataFrame({
            'ts_code': ['000001.SZ'],
            'ann_date': ['20250124'],
            'end_date': ['20241231'],
            'n_cashflow_act': [100000000.0],
            'n_cashflow_inv_act': [-50000000.0],
            'f_cashflow_act': [-20000000.0],
        })
        assert storage.save_cashflow_statement('000001.SZ', '20241231', df)
        result = storage.get_cashflow_statement('000001.SZ')
        assert len(result) == 1
        assert result.iloc[0]['n_cashflow_act'] == 100000000.0

    def test_get_existing_financial_periods(self, storage):
        df1 = pd.DataFrame({'ts_code': ['000001.SZ'], 'end_date': ['20241231'], 'total_assets': [1.0]})
        df2 = pd.DataFrame({'ts_code': ['000001.SZ'], 'end_date': ['20240930'], 'total_assets': [1.0]})
        df3 = pd.DataFrame({'ts_code': ['600519.SH'], 'end_date': ['20241231'], 'total_assets': [1.0]})
        storage.save_balance_sheet('000001.SZ', '20241231', df1)
        storage.save_balance_sheet('000001.SZ', '20240930', df2)
        storage.save_balance_sheet('600519.SH', '20241231', df3)
        existing = storage.get_existing_financial_periods()
        assert '000001.SZ' in existing
        assert '600519.SH' in existing
        assert existing['000001.SZ'] == {'20241231', '20240930'}
        assert existing['600519.SH'] == {'20241231'}

    def test_save_empty_df_returns_false(self, storage):
        assert not storage.save_balance_sheet('000001.SZ', '20241231', pd.DataFrame())

    def test_get_nonexistent_symbol_returns_empty(self, storage):
        result = storage.get_balance_sheet('999999.SZ')
        assert result.empty
