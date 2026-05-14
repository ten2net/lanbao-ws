# Tushare 财务三大报表同步实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为数据同步节点新增 Tushare 财务三大报表（资产负债表、利润表、现金流量表）的定期全量同步功能，遵守 80次/分钟 速率限制，数据存入 DuckDB。

**Architecture:** 在现有 `DataSyncNode` 内新增独立的财务同步流水线，复用现有节点基础设施（定时调度、手动触发、进度报告）。`TushareAdapter` 新增 3 个财务接口并使用更严格的限流，`DuckDBStorage` 新增 3 张表和 6 个存取方法。

**Tech Stack:** Python 3.10, ROS2 Humble, Tushare, DuckDB, pandas, pytest

---

## 文件结构

| 文件 | 变更 | 职责 |
|------|------|------|
| `src/lanbao_data/lanbao_data/tushare_adapter.py` | 修改 | 新增 `get_balance_sheet()`、`get_income_statement()`、`get_cashflow_statement()` 及财务限流 |
| `src/lanbao_data/lanbao_data/duckdb_storage.py` | 修改 | 新增 `balance_sheet`/`income_statement`/`cashflow_statement` 表及 6 个存取方法 |
| `src/lanbao_data/lanbao_data/data_sync_node.py` | 修改 | 新增配置加载、`_sync_financial_job()`、`_build_financial_sync_tasks()`、触发器 |
| `config/lanbao.yaml` | 修改 | 新增 `financial_sync` 配置块 |
| `tests/test_data_sync/test_tushare_financial.py` | 新建 | `TushareAdapter` 财务接口单元测试 |
| `tests/test_data_sync/test_storage_financial.py` | 新建 | `DuckDBStorage` 财务表 CRUD 单元测试 |
| `tests/test_data_sync/test_financial_sync.py` | 新建 | `DataSyncNode` 财务同步逻辑单元测试 |

---

## Task 1: TushareAdapter 财务接口与限流

**Files:**
- Modify: `src/lanbao_data/lanbao_data/tushare_adapter.py`
- Test: `tests/test_data_sync/test_tushare_financial.py`

- [ ] **Step 1: 编写 TushareAdapter 财务接口测试**

创建测试文件：

```python
# tests/test_data_sync/test_tushare_financial.py
import os
import sys
import time
import pytest
from unittest.mock import Mock, patch
import pandas as pd

# 确保能导入 src 下的模块
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src'))

from lanbao_data.tushare_adapter import TushareAdapter


class TestTushareAdapterFinancial:
    @patch('lanbao_data.tushare_adapter.ts.pro_api')
    def test_get_balance_sheet(self, mock_pro_api):
        """测试获取资产负债表，验证核心字段提取和原始数据保留"""
        mock_pro = Mock()
        mock_pro_api.return_value = mock_pro

        mock_df = pd.DataFrame({
            'ts_code': ['000001.SZ'],
            'ann_date': ['20250124'],
            'end_date': ['20241231'],
            'total_assets': [5000000000.0],
            'total_liab': [3000000000.0],
            'total_hldr_eqy_exc_min_int': [2000000000.0],
            'extra_field': [123.0],
        })
        mock_pro.balancesheet.return_value = mock_df

        adapter = TushareAdapter(api_token='test_token')
        result = adapter.get_balance_sheet('000001.SZ', period='20241231')

        assert not result.empty
        assert result.iloc[0]['total_assets'] == 5000000000.0
        assert result.iloc[0]['total_liab'] == 3000000000.0
        assert 'extra_field' in result.columns
        mock_pro.balancesheet.assert_called_once_with(
            ts_code='000001.SZ',
            period='20241231'
        )

    @patch('lanbao_data.tushare_adapter.ts.pro_api')
    def test_get_income_statement(self, mock_pro_api):
        """测试获取利润表"""
        mock_pro = Mock()
        mock_pro_api.return_value = mock_pro

        mock_df = pd.DataFrame({
            'ts_code': ['000001.SZ'],
            'ann_date': ['20250124'],
            'end_date': ['20241231'],
            'revenue': [1000000000.0],
            'operate_profit': [200000000.0],
            'net_income': [150000000.0],
        })
        mock_pro.income.return_value = mock_df

        adapter = TushareAdapter(api_token='test_token')
        result = adapter.get_income_statement('000001.SZ', period='20241231')

        assert not result.empty
        assert result.iloc[0]['revenue'] == 1000000000.0
        mock_pro.income.assert_called_once_with(
            ts_code='000001.SZ',
            period='20241231'
        )

    @patch('lanbao_data.tushare_adapter.ts.pro_api')
    def test_get_cashflow_statement(self, mock_pro_api):
        """测试获取现金流量表"""
        mock_pro = Mock()
        mock_pro_api.return_value = mock_pro

        mock_df = pd.DataFrame({
            'ts_code': ['000001.SZ'],
            'ann_date': ['20250124'],
            'end_date': ['20241231'],
            'n_cashflow_act': [100000000.0],
            'n_cashflow_inv_act': [-50000000.0],
            'f_cashflow_act': [-20000000.0],
        })
        mock_pro.cashflow.return_value = mock_df

        adapter = TushareAdapter(api_token='test_token')
        result = adapter.get_cashflow_statement('000001.SZ', period='20241231')

        assert not result.empty
        assert result.iloc[0]['n_cashflow_act'] == 100000000.0
        mock_pro.cashflow.assert_called_once_with(
            ts_code='000001.SZ',
            period='20241231'
        )

    @patch('lanbao_data.tushare_adapter.ts.pro_api')
    def test_financial_rate_limit(self, mock_pro_api):
        """测试财务接口使用更严格的限流（0.75s间隔）"""
        mock_pro = Mock()
        mock_pro_api.return_value = mock_pro
        mock_pro.balancesheet.return_value = pd.DataFrame({
            'ts_code': ['000001.SZ'],
            'end_date': ['20241231'],
            'total_assets': [1.0],
        })

        adapter = TushareAdapter(api_token='test_token')

        start = time.time()
        adapter.get_balance_sheet('000001.SZ', period='20241231')
        adapter.get_balance_sheet('000001.SZ', period='20240930')
        elapsed = time.time() - start

        assert elapsed >= 0.75, f"财务接口限流失效，实际间隔 {elapsed:.3f}s"

    @patch('lanbao_data.tushare_adapter.ts.pro_api')
    def test_daily_rate_limit_unchanged(self, mock_pro_api):
        """测试日线接口限流不受影响（仍保持 0.1s）"""
        mock_pro = Mock()
        mock_pro_api.return_value = mock_pro
        mock_pro.daily.return_value = pd.DataFrame({
            'ts_code': ['000001.SZ'],
            'trade_date': ['20250124'],
            'open': [10.0],
        })

        adapter = TushareAdapter(api_token='test_token')

        start = time.time()
        adapter.get_daily_data('000001.SZ', '20250124', '20250124')
        adapter.get_daily_data('000001.SZ', '20250123', '20250123')
        elapsed = time.time() - start

        assert elapsed < 0.5, f"日线接口限流被财务接口影响，实际间隔 {elapsed:.3f}s"

    @patch('lanbao_data.tushare_adapter.ts.pro_api')
    def test_empty_response_returns_empty_df(self, mock_pro_api):
        """测试 Tushare 返回空数据时返回空 DataFrame"""
        mock_pro = Mock()
        mock_pro_api.return_value = mock_pro
        mock_pro.balancesheet.return_value = pd.DataFrame()

        adapter = TushareAdapter(api_token='test_token')
        result = adapter.get_balance_sheet('000001.SZ', period='20241231')

        assert result.empty
```

- [ ] **Step 2: 运行测试确认全部失败**

```bash
pytest tests/test_data_sync/test_tushare_financial.py -v
```

Expected: 6 tests FAIL with `AttributeError: 'TushareAdapter' object has no attribute 'get_balance_sheet'`

- [ ] **Step 3: 实现 TushareAdapter 财务接口与限流**

在 `src/lanbao_data/lanbao_data/tushare_adapter.py` 的 `__init__` 方法中新增：

```python
self._financial_interval = 0.75   # 财务接口：80次/min ≈ 0.75s/次
self._last_financial_request = 0  # 财务接口独立计时
```

修改 `_rate_limit` 方法（backward compatible，现有调用不传参默认 False）：

```python
def _rate_limit(self, financial=False):
    """速率限制"""
    interval = self._financial_interval if financial else self._min_interval
    last = self._last_financial_request if financial else self._last_request_time
    elapsed = time.time() - last
    if elapsed < interval:
        time.sleep(interval - elapsed)
    if financial:
        self._last_financial_request = time.time()
    else:
        self._last_request_time = time.time()
```

在文件末尾（`_convert_symbol` 方法之后）新增三个财务接口：

```python
def get_balance_sheet(self, symbol: str, period: str) -> pd.DataFrame:
    """
    获取资产负债表

    Args:
        symbol: 股票代码，如 '000001.SZ'
        period: 报告期，如 '20241231'

    Returns:
        DataFrame 包含资产负债表数据
    """
    try:
        self._rate_limit(financial=True)
        ts_code = self._convert_symbol(symbol)

        df = self._pro.balancesheet(
            ts_code=ts_code,
            period=period
        )

        if df is None or df.empty:
            logger.warning(f"未获取到 {symbol} 的资产负债表: {period}")
            return pd.DataFrame()

        logger.debug(f"获取 {symbol} 资产负债表: {period}, {len(df)} 条")
        return df

    except Exception as e:
        logger.error(f"获取 {symbol} 资产负债表失败 ({period}): {e}")
        return pd.DataFrame()

def get_income_statement(self, symbol: str, period: str) -> pd.DataFrame:
    """
    获取利润表

    Args:
        symbol: 股票代码
        period: 报告期

    Returns:
        DataFrame 包含利润表数据
    """
    try:
        self._rate_limit(financial=True)
        ts_code = self._convert_symbol(symbol)

        df = self._pro.income(
            ts_code=ts_code,
            period=period
        )

        if df is None or df.empty:
            logger.warning(f"未获取到 {symbol} 的利润表: {period}")
            return pd.DataFrame()

        logger.debug(f"获取 {symbol} 利润表: {period}, {len(df)} 条")
        return df

    except Exception as e:
        logger.error(f"获取 {symbol} 利润表失败 ({period}): {e}")
        return pd.DataFrame()

def get_cashflow_statement(self, symbol: str, period: str) -> pd.DataFrame:
    """
    获取现金流量表

    Args:
        symbol: 股票代码
        period: 报告期

    Returns:
        DataFrame 包含现金流量表数据
    """
    try:
        self._rate_limit(financial=True)
        ts_code = self._convert_symbol(symbol)

        df = self._pro.cashflow(
            ts_code=ts_code,
            period=period
        )

        if df is None or df.empty:
            logger.warning(f"未获取到 {symbol} 的现金流量表: {period}")
            return pd.DataFrame()

        logger.debug(f"获取 {symbol} 现金流量表: {period}, {len(df)} 条")
        return df

    except Exception as e:
        logger.error(f"获取 {symbol} 现金流量表失败 ({period}): {e}")
        return pd.DataFrame()
```

- [ ] **Step 4: 运行测试确认全部通过**

```bash
pytest tests/test_data_sync/test_tushare_financial.py -v
```

Expected: 6 tests PASS

- [ ] **Step 5: 提交**

```bash
git add tests/test_data_sync/test_tushare_financial.py src/lanbao_data/lanbao_data/tushare_adapter.py
git commit -m "feat: add Tushare financial statement APIs with 80 req/min rate limit

- get_balance_sheet(), get_income_statement(), get_cashflow_statement()
- financial=True rate limiting at 0.75s per request
- backward compatible _rate_limit() default behavior

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## Task 2: DuckDBStorage 财务表与存取方法

**Files:**
- Modify: `src/lanbao_data/lanbao_data/duckdb_storage.py`
- Test: `tests/test_data_sync/test_storage_financial.py`

- [ ] **Step 1: 编写 DuckDBStorage 财务表测试**

```python
# tests/test_data_sync/test_storage_financial.py
import os
import sys
import tempfile
import pytest
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src'))

from lanbao_data.duckdb_storage import DuckDBStorage


class TestDuckDBStorageFinancial:
    @pytest.fixture
    def storage(self):
        """创建临时 DuckDB 存储（非只读模式）"""
        with tempfile.NamedTemporaryFile(suffix='.duckdb', delete=False) as f:
            db_path = f.name
        storage = DuckDBStorage(db_path, read_only=False)
        yield storage
        storage.close()
        os.unlink(db_path)

    def test_balance_sheet_crud(self, storage):
        """测试资产负债表存取"""
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
        """测试利润表存取"""
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
        """测试现金流量表存取"""
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
        """测试查询已有财务数据报告期"""
        # 保存两条记录
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
        """测试保存空 DataFrame 返回 False"""
        assert not storage.save_balance_sheet('000001.SZ', '20241231', pd.DataFrame())

    def test_get_nonexistent_symbol_returns_empty(self, storage):
        """测试查询不存在的股票返回空 DataFrame"""
        result = storage.get_balance_sheet('999999.SZ')
        assert result.empty
```

- [ ] **Step 2: 运行测试确认全部失败**

```bash
pytest tests/test_data_sync/test_storage_financial.py -v
```

Expected: 6 tests FAIL with `AttributeError: 'DuckDBStorage' object has no attribute 'save_balance_sheet'`

- [ ] **Step 3: 实现 DuckDBStorage 财务表与存取方法**

在 `src/lanbao_data/lanbao_data/duckdb_storage.py` 的 `_init_tables` 方法中，在现有表创建之后添加三张新表：

```python
# 资产负债表
self._conn.execute("""
    CREATE TABLE IF NOT EXISTS balance_sheet (
        symbol VARCHAR NOT NULL,
        report_period VARCHAR NOT NULL,
        ann_date VARCHAR,
        total_assets DOUBLE,
        total_liab DOUBLE,
        total_hldr_eqy_exc_min_int DOUBLE,
        raw_json VARCHAR,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (symbol, report_period)
    )
""")

# 利润表
self._conn.execute("""
    CREATE TABLE IF NOT EXISTS income_statement (
        symbol VARCHAR NOT NULL,
        report_period VARCHAR NOT NULL,
        ann_date VARCHAR,
        revenue DOUBLE,
        operate_profit DOUBLE,
        net_income DOUBLE,
        raw_json VARCHAR,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (symbol, report_period)
    )
""")

# 现金流量表
self._conn.execute("""
    CREATE TABLE IF NOT EXISTS cashflow_statement (
        symbol VARCHAR NOT NULL,
        report_period VARCHAR NOT NULL,
        ann_date VARCHAR,
        n_cashflow_act DOUBLE,
        n_cashflow_inv_act DOUBLE,
        f_cashflow_act DOUBLE,
        raw_json VARCHAR,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (symbol, report_period)
    )
""")
```

在 `DuckDBStorage` 类中新增 7 个方法（放在 `save_research_report` 之前）：

```python
def save_balance_sheet(self, symbol: str, period: str, data: pd.DataFrame) -> bool:
    """
    保存资产负债表

    Args:
        symbol: 股票代码
        period: 报告期 (YYYYMMDD)
        data: Tushare 返回的 DataFrame

    Returns:
        是否成功
    """
    return self._save_financial_table('balance_sheet', symbol, period, data)

def get_balance_sheet(self, symbol: str, period: Optional[str] = None) -> pd.DataFrame:
    """获取资产负债表"""
    return self._get_financial_table('balance_sheet', symbol, period)

def save_income_statement(self, symbol: str, period: str, data: pd.DataFrame) -> bool:
    """保存利润表"""
    return self._save_financial_table('income_statement', symbol, period, data)

def get_income_statement(self, symbol: str, period: Optional[str] = None) -> pd.DataFrame:
    """获取利润表"""
    return self._get_financial_table('income_statement', symbol, period)

def save_cashflow_statement(self, symbol: str, period: str, data: pd.DataFrame) -> bool:
    """保存现金流量表"""
    return self._save_financial_table('cashflow_statement', symbol, period, data)

def get_cashflow_statement(self, symbol: str, period: Optional[str] = None) -> pd.DataFrame:
    """获取现金流量表"""
    return self._get_financial_table('cashflow_statement', symbol, period)

def _save_financial_table(self, table: str, symbol: str, period: str, data: pd.DataFrame) -> bool:
    """通用财务表保存逻辑"""
    try:
        if data.empty:
            return False

        df = data.copy()

        # 提取核心字段（如果存在）
        ann_date = df['ann_date'].iloc[0] if 'ann_date' in df.columns else None

        # 构建 raw_json（完整原始数据）
        raw_json = json.dumps(df.to_dict(orient='records'), ensure_ascii=False)

        # 准备插入数据
        if table == 'balance_sheet':
            total_assets = float(df['total_assets'].iloc[0]) if 'total_assets' in df.columns else None
            total_liab = float(df['total_liab'].iloc[0]) if 'total_liab' in df.columns else None
            total_eqy = float(df['total_hldr_eqy_exc_min_int'].iloc[0]) if 'total_hldr_eqy_exc_min_int' in df.columns else None

            self._conn.execute(f"""
                INSERT OR REPLACE INTO {table} (symbol, report_period, ann_date, total_assets, total_liab, total_hldr_eqy_exc_min_int, raw_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, [symbol, period, ann_date, total_assets, total_liab, total_eqy, raw_json])

        elif table == 'income_statement':
            revenue = float(df['revenue'].iloc[0]) if 'revenue' in df.columns else None
            operate_profit = float(df['operate_profit'].iloc[0]) if 'operate_profit' in df.columns else None
            net_income = float(df['net_income'].iloc[0]) if 'net_income' in df.columns else None

            self._conn.execute(f"""
                INSERT OR REPLACE INTO {table} (symbol, report_period, ann_date, revenue, operate_profit, net_income, raw_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, [symbol, period, ann_date, revenue, operate_profit, net_income, raw_json])

        elif table == 'cashflow_statement':
            n_cashflow_act = float(df['n_cashflow_act'].iloc[0]) if 'n_cashflow_act' in df.columns else None
            n_cashflow_inv = float(df['n_cashflow_inv_act'].iloc[0]) if 'n_cashflow_inv_act' in df.columns else None
            f_cashflow = float(df['f_cashflow_act'].iloc[0]) if 'f_cashflow_act' in df.columns else None

            self._conn.execute(f"""
                INSERT OR REPLACE INTO {table} (symbol, report_period, ann_date, n_cashflow_act, n_cashflow_inv_act, f_cashflow_act, raw_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, [symbol, period, ann_date, n_cashflow_act, n_cashflow_inv, f_cashflow, raw_json])

        logger.debug(f"保存 {symbol} {table}: {period}")
        return True

    except Exception as e:
        logger.error(f"保存 {symbol} {table} 失败 ({period}): {e}")
        return False

def _get_financial_table(self, table: str, symbol: str, period: Optional[str] = None) -> pd.DataFrame:
    """通用财务表查询逻辑"""
    try:
        query = f"SELECT * FROM {table} WHERE symbol = ?"
        params = [symbol]

        if period:
            query += " AND report_period = ?"
            params.append(period)

        query += " ORDER BY report_period DESC"

        return self._conn.execute(query, params).fetchdf()

    except Exception as e:
        logger.error(f"查询 {symbol} {table} 失败: {e}")
        return pd.DataFrame()

def get_existing_financial_periods(self) -> Dict[str, set]:
    """
    获取所有股票已有的财务数据报告期

    Returns:
        Dict[str, Set[str]]: {symbol: {period1, period2, ...}}
    """
    try:
        tables = ['balance_sheet', 'income_statement', 'cashflow_statement']
        all_periods: Dict[str, set] = {}

        for table in tables:
            result = self._conn.execute(f"""
                SELECT DISTINCT symbol, report_period FROM {table}
            """).fetchall()

            for symbol, period in result:
                if symbol not in all_periods:
                    all_periods[symbol] = set()
                all_periods[symbol].add(period)

        return all_periods

    except Exception as e:
        logger.error(f"查询已有财务报告期失败: {e}")
        return {}
```

- [ ] **Step 4: 运行测试确认全部通过**

```bash
pytest tests/test_data_sync/test_storage_financial.py -v
```

Expected: 6 tests PASS

- [ ] **Step 5: 提交**

```bash
git add tests/test_data_sync/test_storage_financial.py src/lanbao_data/lanbao_data/duckdb_storage.py
git commit -m "feat: add DuckDB financial statement tables and storage methods

- balance_sheet, income_statement, cashflow_statement tables
- 6 CRUD methods + get_existing_financial_periods for incremental sync
- core fields as columns + raw_json for complete data preservation

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## Task 3: DataSyncNode 报告期生成与任务构建

**Files:**
- Modify: `src/lanbao_data/lanbao_data/data_sync_node.py`
- Test: `tests/test_data_sync/test_financial_sync.py`

- [ ] **Step 1: 编写报告期生成和任务构建测试**

```python
# tests/test_data_sync/test_financial_sync.py
import os
import sys
import pytest
from unittest.mock import Mock, patch, MagicMock
import pandas as pd
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src'))

from lanbao_data.data_sync_node import DataSyncNode


class TestFinancialSyncLogic:
    @patch('lanbao_data.data_sync_node.TushareAdapter')
    @patch('lanbao_data.data_sync_node.LanBaoBaseNode.__init__', return_value=None)
    def test_generate_report_periods(self, mock_base_init, mock_adapter_cls):
        """测试报告期生成"""
        node = DataSyncNode.__new__(DataSyncNode)
        node._financial_start_period = '20200101'

        periods = node._generate_report_periods('20200101')

        # 应该包含 2020Q1 到当前日期前一季度的所有报告期
        assert '20200331' in periods
        assert '20201231' in periods
        # 当前日期是 2026-05-15，应该包含 2026Q1 (20250331)，不包含 2026Q2 (20250630)
        assert '20250331' in periods

    @patch('lanbao_data.data_sync_node.TushareAdapter')
    @patch('lanbao_data.data_sync_node.LanBaoBaseNode.__init__', return_value=None)
    def test_build_financial_sync_tasks(self, mock_base_init, mock_adapter_cls):
        """测试同步任务构建：已有数据跳过，只生成缺失的任务"""
        node = DataSyncNode.__new__(DataSyncNode)
        node._financial_start_period = '20241201'

        # 模拟股票列表
        stock_list = pd.DataFrame({
            'symbol': ['000001.SZ', '600519.SH'],
        })

        # Mock DuckDBStorage
        mock_storage = Mock()
        mock_storage.get_existing_financial_periods.return_value = {
            '000001.SZ': {'20241231'},
        }

        with patch('lanbao_data.data_sync_node.DuckDBStorage', return_value=mock_storage):
            tasks = node._build_financial_sync_tasks(stock_list)

        # 000001.SZ 已有 2024Q4，不应生成任务
        # 600519.SH 没有数据，应生成 2024Q4 任务
        symbols = [t['symbol'] for t in tasks]
        assert '600519.SH' in symbols
        assert '000001.SZ' not in symbols or not any(t['symbol'] == '000001.SZ' and t['period'] == '20241231' for t in tasks)

    @patch('lanbao_data.data_sync_node.TushareAdapter')
    @patch('lanbao_data.data_sync_node.LanBaoBaseNode.__init__', return_value=None)
    def test_build_tasks_empty_stock_list(self, mock_base_init, mock_adapter_cls):
        """测试空股票列表返回空任务"""
        node = DataSyncNode.__new__(DataSyncNode)
        node._financial_start_period = '20200101'

        stock_list = pd.DataFrame({'symbol': []})
        tasks = node._build_financial_sync_tasks(stock_list)

        assert tasks == []
```

- [ ] **Step 2: 运行测试确认失败**

```bash
pytest tests/test_data_sync/test_financial_sync.py -v
```

Expected: 3 tests FAIL with `AttributeError: 'DataSyncNode' object has no attribute '_generate_report_periods'`

- [ ] **Step 3: 实现 DataSyncNode 财务同步配置加载与工具方法**

在 `src/lanbao_data/lanbao_data/data_sync_node.py` 的 `__init__` 方法中，在现有配置初始化之后添加：

```python
# 财务同步配置
self._financial_sync_enabled = True
self._financial_sync_day = 'sun'
self._financial_sync_time = '02:00'
self._financial_start_period = '20200101'
self._financial_run_on_startup = False
self._financial_batch_interval = 100

# 财务同步运行状态
self._financial_sync_thread: Optional[threading.Thread] = None
self._financial_sync_running = False
self._last_financial_sync_time: Optional[datetime] = None
self._financial_sync_stats: Dict[str, Any] = {}

# 财务同步定时器
self._financial_schedule_timer = None
```

在 `_load_config` 方法中，在现有配置加载之后添加：

```python
# 加载财务同步配置
financial_config = config.get('data_sync', {}).get('financial_sync', {})
self._financial_sync_enabled = financial_config.get('enabled', True)
self._financial_sync_day = financial_config.get('sync_day', 'sun')
self._financial_sync_time = financial_config.get('sync_time', '02:00')
self._financial_start_period = financial_config.get('start_period', '20200101')
self._financial_run_on_startup = financial_config.get('run_on_startup', False)
self._financial_batch_interval = financial_config.get('batch_report_interval', 100)

logger.info(f"加载财务同步配置: enabled={self._financial_sync_enabled}, "
           f"day={self._financial_sync_day}, time={self._financial_sync_time}")
```

在 `DataSyncNode` 类中新增报告期生成和任务构建方法：

```python
def _generate_report_periods(self, start_date_str: str) -> List[str]:
    """
    生成从起始日期到当前日期的所有季度末报告期

    Args:
        start_date_str: 起始日期 'YYYYMMDD'

    Returns:
        报告期列表 ['YYYYMMDD', ...]
    """
    start_year = int(start_date_str[:4])
    current_date = datetime.now()
    current_year = current_date.year

    periods = []
    for year in range(start_year, current_year + 1):
        for month, day in [(3, 31), (6, 30), (9, 30), (12, 31)]:
            period_date = datetime(year, month, day)
            if period_date <= current_date:
                periods.append(period_date.strftime('%Y%m%d'))

    return periods

def _build_financial_sync_tasks(self, stock_list: pd.DataFrame) -> List[Dict[str, Any]]:
    """
    构建财务同步任务，只同步缺失的报告期

    Args:
        stock_list: 股票列表 DataFrame

    Returns:
        同步任务列表，每个任务包含 symbol 和 period
    """
    periods = self._generate_report_periods(self._financial_start_period)
    if not periods:
        return []

    read_storage = None
    existing: Dict[str, set] = {}

    try:
        db_path = os.getenv('DUCKDB_PATH', './data/lanbao.duckdb')
        read_storage = DuckDBStorage(db_path, read_only=True)
        existing = read_storage.get_existing_financial_periods()
    except Exception as e:
        logger.warning(f"读取已有财务数据失败，将全量同步: {e}")
    finally:
        if read_storage:
            read_storage.close()

    tasks = []
    for _, row in stock_list.iterrows():
        symbol = row['symbol']
        symbol_existing = existing.get(symbol, set())
        for period in periods:
            if period not in symbol_existing:
                tasks.append({
                    'symbol': symbol,
                    'period': period
                })

    logger.info(f"财务同步任务: 共 {len(tasks)} 个 (股票 {len(stock_list)} 只, 报告期 {len(periods)} 个)")
    return tasks
```

- [ ] **Step 4: 运行测试确认通过**

```bash
pytest tests/test_data_sync/test_financial_sync.py -v
```

Expected: 3 tests PASS

- [ ] **Step 5: 提交**

```bash
git add tests/test_data_sync/test_financial_sync.py src/lanbao_data/lanbao_data/data_sync_node.py
git commit -m "feat: add financial sync period generation and task building

- _generate_report_periods(): quarterly periods from 2020 to present
- _build_financial_sync_tasks(): incremental sync based on existing DB data
- financial sync config loading from YAML

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## Task 4: DataSyncNode 财务同步任务执行与触发器

**Files:**
- Modify: `src/lanbao_data/lanbao_data/data_sync_node.py`
- Test: `tests/test_data_sync/test_financial_sync.py`

- [ ] **Step 1: 编写财务同步任务执行和触发器测试**

在 `tests/test_data_sync/test_financial_sync.py` 中追加：

```python
    @patch('lanbao_data.data_sync_node.TushareAdapter')
    @patch('lanbao_data.data_sync_node.LanBaoBaseNode.__init__', return_value=None)
    def test_should_sync_financial_today(self, mock_base_init, mock_adapter_cls):
        """测试周日判断逻辑"""
        node = DataSyncNode.__new__(DataSyncNode)
        node._financial_sync_enabled = True
        node._financial_sync_running = False
        node._financial_sync_day = 'sun'
        node._financial_sync_time = '02:00'
        node._last_financial_sync_time = None

        # 模拟周日凌晨 3 点
        with patch('lanbao_data.data_sync_node.datetime') as mock_dt:
            mock_now = Mock()
            mock_now.strftime.return_value = 'sun'
            mock_now.strftime.return_value = '03:00'
            mock_now.date.return_value = datetime(2026, 5, 10).date()  # 周日
            mock_dt.now.return_value = mock_now
            mock_dt.strptime = datetime.strptime

            assert node._should_sync_financial_today()

    @patch('lanbao_data.data_sync_node.TushareAdapter')
    @patch('lanbao_data.data_sync_node.LanBaoBaseNode.__init__', return_value=None)
    def test_trigger_financial_sync_prevents_duplicate(self, mock_base_init, mock_adapter_cls):
        """测试重复触发被阻止"""
        node = DataSyncNode.__new__(DataSyncNode)
        node._financial_sync_running = True

        node._trigger_financial_sync()
        # 不应抛出异常，只是跳过
        assert node._financial_sync_running
```

- [ ] **Step 2: 运行测试确认失败**

```bash
pytest tests/test_data_sync/test_financial_sync.py::TestFinancialSyncLogic::test_should_sync_financial_today tests/test_data_sync/test_financial_sync.py::TestFinancialSyncLogic::test_trigger_financial_sync_prevents_duplicate -v
```

Expected: 2 tests FAIL with `AttributeError`

- [ ] **Step 3: 实现财务同步任务执行与触发器**

在 `start` 方法中，在现有触发器注册之后添加：

```python
# 注册财务同步手动触发订阅
self._financial_sync_trigger_sub = self.create_subscription(
    StdString,
    '/data/trigger_financial_sync',
    self._on_financial_sync_trigger,
    10
)
logger.info("已注册财务同步手动触发订阅: /data/trigger_financial_sync")
```

修改 `start` 方法中的定时器创建，改为一个统一的调度检查定时器（如果已有多个定时器则保留原样，新增一个财务同步检查定时器）：

```python
# 创建财务同步定时器（每分钟检查）
self._financial_schedule_timer = self.create_timer(
    60.0,
    self._on_financial_schedule_check,
    callback_group=self._callback_group
)

# 启动时执行一次财务同步（如果配置启用）
if self._financial_run_on_startup:
    logger.info("配置为启动时立即执行财务同步")
    self._trigger_financial_sync()
else:
    if self._should_sync_financial_today():
        logger.info(f"今天符合财务同步条件 ({self._financial_sync_day} {self._financial_sync_time})，立即补同步")
        self._trigger_financial_sync()
    else:
        logger.info(f"财务同步已配置，将在每周 {self._financial_sync_day} {self._financial_sync_time} 执行")
```

在 `stop` 方法中，在现有清理之后添加：

```python
# 等待财务同步线程结束
if self._financial_sync_thread and self._financial_sync_thread.is_alive():
    logger.info("等待财务同步线程结束...")
    self._financial_sync_running = False
    self._financial_sync_thread.join(timeout=30)

# 销毁财务同步定时器
if self._financial_schedule_timer:
    self.destroy_timer(self._financial_schedule_timer)
```

在 `DataSyncNode` 类中新增触发器和调度方法：

```python
def _should_sync_financial_today(self) -> bool:
    """判断今天是否需要执行财务同步"""
    if not self._financial_sync_enabled or self._financial_sync_running:
        return False

    now = datetime.now()
    current_time = now.strftime('%H:%M')
    current_weekday = now.strftime('%a').lower()[:3]  # 'mon', 'tue', etc.

    # 检查是否是配置的星期
    day_map = {
        'mon': 'mon', 'tue': 'tue', 'wed': 'wed',
        'thu': 'thu', 'fri': 'fri', 'sat': 'sat', 'sun': 'sun'
    }
    target_day = day_map.get(self._financial_sync_day.lower(), 'sun')
    if current_weekday != target_day:
        return False

    # 检查是否已过同步时间
    if current_time < self._financial_sync_time:
        return False

    # 检查本周是否已同步过
    if self._last_financial_sync_time:
        last_date = self._last_financial_sync_time.date()
        today = now.date()
        if last_date == today:
            return False

    return True

def _on_financial_schedule_check(self):
    """定时检查是否到达财务同步时间"""
    if not self._financial_sync_enabled or self._financial_sync_running:
        return

    if self._should_sync_financial_today():
        self._trigger_financial_sync()

def _on_financial_sync_trigger(self, msg: StdString):
    """接收财务同步手动触发消息"""
    logger.info(f"收到财务同步手动触发请求: {msg.data}")
    self._trigger_financial_sync()

def _trigger_financial_sync(self):
    """触发财务同步后台任务"""
    if self._financial_sync_running:
        logger.warning("财务同步任务已在运行中，跳过本次触发")
        return

    self._financial_sync_running = True
    self._last_financial_sync_time = datetime.now()

    self._financial_sync_thread = threading.Thread(
        target=self._sync_financial_job,
        daemon=True
    )
    self._financial_sync_thread.start()

    logger.info("财务同步后台任务已启动")
```

在 `DataSyncNode` 类中新增核心同步任务方法（放在 `_sync_job` 之后）：

```python
def _sync_financial_job(self):
    """
    执行财务数据同步任务（在后台线程中运行）
    """
    start_time = time.time()
    total_symbols = 0
    success_count = 0
    failed_count = 0
    write_storage = None

    try:
        self._status.status = "SYNCING_FINANCIAL"

        # 步骤1: 获取全部A股列表
        logger.info("正在获取A股股票列表（财务同步）...")
        stock_list = self._adapter.get_stock_list(market='A')

        if stock_list.empty:
            logger.error("获取股票列表失败，财务同步终止")
            return

        total_symbols = len(stock_list)
        logger.info(f"获取到 {total_symbols} 只股票")

        # 步骤2: 计算增量更新范围
        logger.info("计算财务数据增量更新范围...")
        sync_tasks = self._build_financial_sync_tasks(stock_list)
        logger.info(f"需要同步的财务数据: {len(sync_tasks)} 条")

        if not sync_tasks:
            logger.info("财务数据已是最新，无需同步")
            return

        # 步骤3: 关闭只读连接，获取写入连接
        logger.info("正在获取数据库写入权限（财务同步）...")
        db_path = os.getenv('DUCKDB_PATH', './data/lanbao.duckdb')

        if self._storage:
            self._storage.close()
            self._storage = None

        for attempt in range(60):
            try:
                write_storage = DuckDBStorage(db_path, read_only=False)
                logger.info("获取数据库写入权限成功（财务同步）")
                break
            except Exception as e:
                if attempt < 59:
                    logger.debug(f"等待数据库锁释放... ({attempt+1}/60)")
                    time.sleep(1)
                else:
                    raise RuntimeError(f"无法获取数据库写入权限: {e}")

        if not write_storage:
            raise RuntimeError("无法获取数据库写入权限")

        # 步骤4: 执行批量下载和写入
        for i, task in enumerate(sync_tasks):
            symbol = task['symbol']
            period = task['period']

            try:
                # 下载三张报表
                bs_data = self._adapter.get_balance_sheet(symbol, period=period)
                inc_data = self._adapter.get_income_statement(symbol, period=period)
                cf_data = self._adapter.get_cashflow_statement(symbol, period=period)

                # 保存到数据库
                saved = 0
                if not bs_data.empty:
                    if write_storage.save_balance_sheet(symbol, period, bs_data):
                        saved += 1
                if not inc_data.empty:
                    if write_storage.save_income_statement(symbol, period, inc_data):
                        saved += 1
                if not cf_data.empty:
                    if write_storage.save_cashflow_statement(symbol, period, cf_data):
                        saved += 1

                if saved == 3:
                    success_count += 1
                else:
                    failed_count += 1
                    logger.warning(f"[{i+1}/{len(sync_tasks)}] {symbol} {period}: 部分报表缺失 ({saved}/3)")

                # 定期报告进度
                if (i + 1) % self._financial_batch_interval == 0:
                    progress = (i + 1) / len(sync_tasks) * 100
                    elapsed = time.time() - start_time
                    rate = (i + 1) / elapsed if elapsed > 0 else 0
                    remaining = (len(sync_tasks) - (i + 1)) / rate if rate > 0 else 0
                    logger.info(f"财务同步进度: {i+1}/{len(sync_tasks)} ({progress:.1f}%), "
                               f"成功 {success_count}, 失败 {failed_count}, "
                               f"预计剩余 {remaining/60:.0f}分钟")

            except Exception as e:
                logger.error(f"[{i+1}/{len(sync_tasks)}] {symbol} {period}: 同步失败 - {e}")
                failed_count += 1

        elapsed = time.time() - start_time
        message = (f"财务同步完成: 成功 {success_count}/{len(sync_tasks)}, "
                  f"失败 {failed_count}, 耗时 {elapsed:.1f}秒")
        logger.info(message)
        self._publish_alert("INFO", message, component="data_sync_financial")

    except Exception as e:
        elapsed = time.time() - start_time
        message = f"财务同步异常: {str(e)}, 耗时 {elapsed:.1f}秒"
        logger.error(message)
        self._publish_alert("ERROR", message, component="data_sync_financial")

    finally:
        if write_storage:
            write_storage.close()

        self._financial_sync_running = False
        self._financial_sync_stats = {
            'total': total_symbols,
            'synced': success_count,
            'failed': failed_count,
            'elapsed': time.time() - start_time,
            'last_sync': datetime.now().isoformat()
        }
        self._status.status = "RUNNING"
```

- [ ] **Step 4: 运行测试确认通过**

```bash
pytest tests/test_data_sync/test_financial_sync.py -v
```

Expected: 5 tests PASS

- [ ] **Step 5: 提交**

```bash
git add tests/test_data_sync/test_financial_sync.py src/lanbao_data/lanbao_data/data_sync_node.py
git commit -m "feat: add financial sync job execution and triggers

- _sync_financial_job(): background thread for quarterly financial sync
- _should_sync_financial_today(): weekly schedule check
- Manual trigger via /data/trigger_financial_sync topic
- Progress reporting every N stocks with ETA
- Independent sync stats and status tracking

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## Task 5: 配置文件更新

**Files:**
- Modify: `config/lanbao.yaml`

- [ ] **Step 1: 修改配置文件**

在 `config/lanbao.yaml` 的 `data_sync` 配置块中，在 `max_workers: 1` 之后追加：

```yaml
  # 财务同步配置
  financial_sync:
    enabled: true
    sync_day: 'sun'           # 周日执行（mon/tue/wed/thu/fri/sat/sun）
    sync_time: '02:00'        # 凌晨 2 点
    start_period: '20200101'  # 最早报告期
    run_on_startup: false
    batch_report_interval: 100  # 每 100 只股票报告进度
```

- [ ] **Step 2: 验证配置加载**

```bash
python -c "
import yaml
with open('config/lanbao.yaml') as f:
    config = yaml.safe_load(f)
fs = config['data_sync']['financial_sync']
print(f'enabled={fs[\"enabled\"]}')
print(f'sync_day={fs[\"sync_day\"]}')
print(f'sync_time={fs[\"sync_time\"]}')
print(f'start_period={fs[\"start_period\"]}')
print('Config OK')
"
```

Expected:
```
enabled=True
sync_day=sun
sync_time=02:00
start_period=20200101
Config OK
```

- [ ] **Step 3: 提交**

```bash
git add config/lanbao.yaml
git commit -m "config: add financial_sync configuration block

- Weekly auto sync on Sunday at 02:00
- Configurable start_period, batch interval, startup behavior

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## Task 6: 运行全量测试并验证

**Files:**
- Test: `tests/test_data_sync/`

- [ ] **Step 1: 运行全部数据同步测试**

```bash
pytest tests/test_data_sync/ -v
```

Expected: 17 tests PASS (6 + 6 + 5)

- [ ] **Step 2: 运行类型检查**

```bash
mypy src/lanbao_data/lanbao_data/tushare_adapter.py src/lanbao_data/lanbao_data/duckdb_storage.py src/lanbao_data/lanbao_data/data_sync_node.py --ignore-missing-imports
```

Expected: No errors (可能有一些 ROS2 相关的 missing import 警告，可以忽略)

- [ ] **Step 3: 运行代码格式化**

```bash
black src/lanbao_data/lanbao_data/tushare_adapter.py src/lanbao_data/lanbao_data/duckdb_storage.py src/lanbao_data/lanbao_data/data_sync_node.py tests/test_data_sync/
```

Expected: 4 files reformatted (或 already formatted)

- [ ] **Step 4: 提交格式化结果**

```bash
git add -A
git commit -m "style: format financial sync code with black

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## 自检

### Spec 覆盖检查

| Spec 要求 | 对应 Task |
|-----------|-----------|
| TushareAdapter 新增 3 个财务接口 | Task 1 |
| 财务接口 80次/分钟 限流 | Task 1 (_rate_limit with financial=True) |
| DuckDB 新增 3 张表 | Task 2 (_init_tables) |
| 核心字段单独列 + raw_json | Task 2 (_save_financial_table) |
| 全市场从 2020 年开始同步 | Task 3 (_generate_report_periods) |
| 增量同步（跳过已有报告期） | Task 3 (_build_financial_sync_tasks + get_existing_financial_periods) |
| 每周日凌晨自动同步 | Task 4 (_should_sync_financial_today) |
| 手动触发（Topic） | Task 4 (_on_financial_sync_trigger) |
| 进度报告 | Task 4 (_sync_financial_job logging) |
| 配置文件 | Task 5 |
| 单元测试覆盖 | All Tasks |

### Placeholder 扫描

无 TBD、TODO、"implement later"、"appropriate error handling" 等占位符。每个步骤包含完整代码。

### 类型一致性检查

- `TushareAdapter._rate_limit(financial=False)` 签名一致
- `DuckDBStorage` 新增方法签名：`save_*(symbol, period, data)` / `get_*(symbol, period=None)`
- `DataSyncNode` 配置属性名：`_*financial_*` 前缀一致
- 报告期格式：`YYYYMMDD` 字符串，全文档一致
