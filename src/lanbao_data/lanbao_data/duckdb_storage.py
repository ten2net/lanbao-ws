"""
DuckDB数据存储模块
提供高性能的本地数据存储和查询
"""
import os
import time
import json
import duckdb
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Optional, List, Dict, Any
from pathlib import Path
from loguru import logger

from .duckdb_lock import db_lock


class DuckDBStorage:
    """
    DuckDB存储管理器
    
    功能:
    - 股票数据存储
    - 高效查询
    - 数据缓存
    """
    
    def __init__(self, db_path: str = "./data/lanbao.duckdb", read_only: bool = False, timeout: int = 30):
        """
        初始化DuckDB存储

        Args:
            db_path: 数据库文件路径
            read_only: 是否以只读模式打开
            timeout: 连接超时时间（秒）
        """
        self._db_path = db_path
        self._read_only = read_only
        self._lock_fd = None

        # 确保目录存在
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)

        # 获取文件锁（共享或排他），确保多进程协调访问
        self._acquire_file_lock(timeout)

        # 初始化连接（带重试）
        self._conn = self._connect_with_retry(timeout)

        # 初始化表结构
        if not read_only:
            self._init_tables()

        logger.info(f"DuckDB存储初始化完成: {db_path} (read_only={read_only})")
    
    def _acquire_file_lock(self, timeout: int):
        """获取操作系统文件锁（共享或排他）"""
        import fcntl

        lock_file = f"{self._db_path}.lock"
        lock_cmd = fcntl.LOCK_SH if self._read_only else fcntl.LOCK_EX
        self._lock_fd = os.open(lock_file, os.O_CREAT | os.O_RDWR)

        start = time.time()
        while time.time() - start < timeout:
            try:
                fcntl.flock(self._lock_fd, lock_cmd | fcntl.LOCK_NB)
                logger.debug(f"获取 {'共享' if self._read_only else '排他'} 文件锁成功")
                return
            except (IOError, OSError):
                time.sleep(0.5)

        raise TimeoutError(
            f"无法获取 DuckDB {'共享' if self._read_only else '排他'} 锁，超时 {timeout}s"
        )

    def _release_file_lock(self):
        """释放操作系统文件锁"""
        import fcntl

        if self._lock_fd is not None:
            try:
                fcntl.flock(self._lock_fd, fcntl.LOCK_UN)
                logger.debug("释放文件锁")
            except Exception:
                pass
            try:
                os.close(self._lock_fd)
            except Exception:
                pass
            self._lock_fd = None

    def _connect_with_retry(self, timeout: int) -> duckdb.DuckDBPyConnection:
        """
        带重试的连接
        
        Args:
            timeout: 超时时间（秒）
            
        Returns:
            DuckDB连接对象
        """
        start_time = time.time()
        last_error = None
        
        while time.time() - start_time < timeout:
            try:
                # 尝试连接
                conn = duckdb.connect(self._db_path, read_only=self._read_only)
                return conn
            except Exception as e:
                last_error = e
                error_msg = str(e).lower()
                
                # 如果是锁冲突，等待后重试
                if "lock" in error_msg or "busy" in error_msg or "conflicting" in error_msg:
                    logger.warning(f"数据库被锁定，等待重试... ({e})")
                    time.sleep(1)
                    continue
                else:
                    # 其他错误直接抛出
                    raise
        
        # 超时后抛出最后一次错误
        logger.error(f"连接数据库超时: {last_error}")
        raise last_error
    
    def _init_tables(self):
        """初始化数据表"""
        # 股票日线数据表（含前复权价格）
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS stock_daily (
                symbol VARCHAR NOT NULL,
                date DATE NOT NULL,
                open DOUBLE,
                high DOUBLE,
                low DOUBLE,
                close DOUBLE,
                volume DOUBLE,
                amount DOUBLE,
                change_pct DOUBLE,
                adj_factor DOUBLE DEFAULT 1.0,
                open_adj DOUBLE,
                high_adj DOUBLE,
                low_adj DOUBLE,
                close_adj DOUBLE,
                data_source VARCHAR,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (symbol, date)
            )
        """)
        
        # 股票基本信息表
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS stock_info (
                symbol VARCHAR PRIMARY KEY,
                name VARCHAR,
                industry VARCHAR,
                market VARCHAR,
                list_date DATE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 回测结果表
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS backtest_results (
                backtest_id VARCHAR PRIMARY KEY,
                strategy_id VARCHAR,
                symbol VARCHAR,
                start_date DATE,
                end_date DATE,
                total_return DOUBLE,
                annual_return DOUBLE,
                sharpe_ratio DOUBLE,
                max_drawdown DOUBLE,
                volatility DOUBLE,
                win_rate DOUBLE,
                trades_count INTEGER,
                params JSON,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 交易记录表
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS trades (
                trade_id VARCHAR PRIMARY KEY,
                backtest_id VARCHAR,
                symbol VARCHAR,
                trade_date DATE,
                action VARCHAR,
                quantity INTEGER,
                price DOUBLE,
                amount DOUBLE,
                commission DOUBLE,
                strategy_id VARCHAR,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 创建索引
        self._conn.execute("CREATE INDEX IF NOT EXISTS idx_stock_daily_symbol ON stock_daily(symbol)")
        self._conn.execute("CREATE INDEX IF NOT EXISTS idx_stock_daily_date ON stock_daily(date)")
        self._conn.execute("CREATE INDEX IF NOT EXISTS idx_backtest_strategy ON backtest_results(strategy_id)")
        
        # 交易日历表
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS trade_calendar (
                trade_date DATE PRIMARY KEY,
                exchange VARCHAR DEFAULT 'SSE',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 数据同步状态表
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS sync_status (
                id INTEGER PRIMARY KEY,
                last_sync_time TIMESTAMP,
                total_symbols INTEGER DEFAULT 0,
                success_count INTEGER DEFAULT 0,
                failed_count INTEGER DEFAULT 0,
                status VARCHAR DEFAULT 'idle',
                message VARCHAR,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 迁移：为旧表添加复权相关列
        self._migrate_stock_daily()

        logger.debug("数据库表结构初始化完成")

    def _migrate_stock_daily(self):
        """为已存在的 stock_daily 表添加复权相关列"""
        try:
            # 检查现有列
            result = self._conn.execute(
                "SELECT column_name FROM information_schema.columns WHERE table_name = 'stock_daily'"
            ).fetchall()
            existing_cols = [row[0] for row in result]

            # 需要添加的新列
            new_columns = {
                'adj_factor': 'DOUBLE DEFAULT 1.0',
                'open_adj': 'DOUBLE',
                'high_adj': 'DOUBLE',
                'low_adj': 'DOUBLE',
                'close_adj': 'DOUBLE'
            }

            for col, col_type in new_columns.items():
                if col not in existing_cols:
                    self._conn.execute(f"ALTER TABLE stock_daily ADD COLUMN {col} {col_type}")
                    logger.info(f"迁移: stock_daily 表添加列 {col}")

                    # 为已有数据填充默认值（原始价格作为前复权价格）
                    if col != 'adj_factor':
                        base_col = col.replace('_adj', '')
                        self._conn.execute(f"""
                            UPDATE stock_daily
                            SET {col} = {base_col}
                            WHERE {col} IS NULL
                        """)

        except Exception as e:
            logger.warning(f"表迁移失败（可能表不存在）: {e}")
    
    def save_daily_data(self, symbol: str, data: pd.DataFrame) -> bool:
        """
        保存日线数据（支持前复权价格）

        Args:
            symbol: 股票代码
            data: DataFrame包含日线数据（含 adj_factor, *_adj 列）

        Returns:
            是否成功
        """
        try:
            if data.empty:
                return False

            # 准备数据
            df = data.copy()
            df['symbol'] = symbol

            # 列名映射：Tushare列名 -> 数据库列名
            column_mapping = {
                'pct_chg': 'change_pct',
                'vol': 'volume'
            }
            df = df.rename(columns=column_mapping)

            # 确保基本列存在
            required_cols = ['symbol', 'date', 'open', 'high', 'low', 'close', 'volume']
            for col in required_cols:
                if col not in df.columns:
                    logger.warning(f"数据缺少必要列: {col}")
                    return False

            # 添加数据源列（如果不存在）
            if 'data_source' not in df.columns:
                df['data_source'] = 'tushare'

            # 确保复权相关列存在（向后兼容）
            for col in ['adj_factor', 'open_adj', 'high_adj', 'low_adj', 'close_adj']:
                if col not in df.columns:
                    if col == 'adj_factor':
                        df[col] = 1.0
                    else:
                        # *_adj 列默认等于原始价格
                        base_col = col.replace('_adj', '')
                        df[col] = df[base_col] if base_col in df.columns else 0.0

            # 删除已存在的数据(增量更新)
            dates = df['date'].tolist()
            if dates:
                date_str = ','.join([f"'{d}'" for d in dates])
                self._conn.execute(f"""
                    DELETE FROM stock_daily
                    WHERE symbol = '{symbol}' AND date IN ({date_str})
                """)

            # 只保留数据库表需要的列，删除多余列避免映射错位
            db_columns = ['symbol', 'date', 'open', 'high', 'low', 'close',
                          'volume', 'amount', 'change_pct', 'adj_factor',
                          'open_adj', 'high_adj', 'low_adj', 'close_adj',
                          'data_source']
            df = df[[col for col in db_columns if col in df.columns]]

            # 插入数据（按列名匹配）
            self._conn.execute("""
                INSERT INTO stock_daily BY NAME
                SELECT * FROM df
            """)

            logger.debug(f"保存 {symbol} 数据: {len(df)} 条")
            return True

        except Exception as e:
            logger.error(f"保存 {symbol} 数据失败: {e}")
            return False
    
    def _normalize_date(self, date_str: Optional[str]) -> Optional[str]:
        """将日期格式统一为 YYYY-MM-DD，兼容 YYYYMMDD 格式"""
        if not date_str:
            return None
        if len(date_str) == 8 and date_str.isdigit():
            return f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]}"
        return date_str

    def get_daily_data(self, symbol: str, start_date: Optional[str] = None,
                       end_date: Optional[str] = None) -> pd.DataFrame:
        """
        获取日线数据

        Args:
            symbol: 股票代码
            start_date: 开始日期 (支持 YYYYMMDD 或 YYYY-MM-DD)
            end_date: 结束日期 (支持 YYYYMMDD 或 YYYY-MM-DD)

        Returns:
            DataFrame包含日线数据
        """
        try:
            query = "SELECT * FROM stock_daily WHERE symbol = ?"
            params = [symbol]

            normalized_start = self._normalize_date(start_date)
            normalized_end = self._normalize_date(end_date)

            if normalized_start:
                query += " AND date >= ?"
                params.append(normalized_start)
            if normalized_end:
                query += " AND date <= ?"
                params.append(normalized_end)

            query += " ORDER BY date"

            df = self._conn.execute(query, params).fetchdf()

            logger.debug(f"查询 {symbol} 数据: {len(df)} 条")
            return df

        except Exception as e:
            logger.error(f"查询 {symbol} 数据失败: {e}")
            return pd.DataFrame()
    
    def get_symbols(self) -> List[str]:
        """获取所有股票代码"""
        try:
            result = self._conn.execute(
                "SELECT DISTINCT symbol FROM stock_daily ORDER BY symbol"
            ).fetchall()
            return [row[0] for row in result]
        except Exception as e:
            logger.error(f"获取股票列表失败: {e}")
            return []
    
    def save_stock_info(self, data: pd.DataFrame) -> bool:
        """
        保存股票基本信息
        
        Args:
            data: DataFrame包含股票信息
            
        Returns:
            是否成功
        """
        try:
            if data.empty:
                return False
            
            df = data.copy()
            
            # 插入或更新
            self._conn.execute("""
                INSERT OR REPLACE INTO stock_info 
                SELECT symbol, name, industry, market, list_date, CURRENT_TIMESTAMP
                FROM df
            """)
            
            logger.info(f"保存股票信息: {len(df)} 条")
            return True
            
        except Exception as e:
            logger.error(f"保存股票信息失败: {e}")
            return False
    
    def save_backtest_result(self, result: Dict[str, Any]) -> bool:
        """
        保存回测结果
        
        Args:
            result: 回测结果字典
            
        Returns:
            是否成功
        """
        try:
            # 数据转换函数
            def _convert_value(value):
                """转换值为数据库兼容格式"""
                if value is None:
                    return None
                # 处理numpy类型
                if isinstance(value, np.floating):
                    return float(value)
                if isinstance(value, np.integer):
                    return int(value)
                if isinstance(value, np.bool_):
                    return bool(value)
                # 处理字典 -> JSON字符串
                if isinstance(value, dict):
                    return json.dumps(value, ensure_ascii=False)
                # 其他类型保持不变
                return value
            
            # 准备插入数据
            params = result.get('params', {})
            # 确保params是字典
            if not isinstance(params, dict):
                params = {}
            
            self._conn.execute("""
                INSERT OR REPLACE INTO backtest_results VALUES (
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP
                )
            """, [
                result['backtest_id'],
                result.get('strategy_id', ''),
                result.get('symbol', ''),
                result.get('start_date'),
                result.get('end_date'),
                _convert_value(result.get('total_return', 0)),
                _convert_value(result.get('annual_return', 0)),
                _convert_value(result.get('sharpe_ratio', 0)),
                _convert_value(result.get('max_drawdown', 0)),
                _convert_value(result.get('volatility', 0)),
                _convert_value(result.get('win_rate', 0)),
                _convert_value(result.get('trades_count', 0)),
                _convert_value(params)
            ])
            
            logger.info(f"保存回测结果: {result['backtest_id']}")
            return True
            
        except Exception as e:
            logger.error(f"保存回测结果失败: {e}")
            return False
    
    def get_backtest_results(self, strategy_id: Optional[str] = None) -> pd.DataFrame:
        """
        获取回测结果
        
        Args:
            strategy_id: 策略ID，为空则获取所有
            
        Returns:
            DataFrame包含回测结果
        """
        try:
            if strategy_id:
                df = self._conn.execute(
                    "SELECT * FROM backtest_results WHERE strategy_id = ? ORDER BY created_at DESC",
                    [strategy_id]
                ).fetchdf()
            else:
                df = self._conn.execute(
                    "SELECT * FROM backtest_results ORDER BY created_at DESC"
                ).fetchdf()
            
            return df
            
        except Exception as e:
            logger.error(f"查询回测结果失败: {e}")
            return pd.DataFrame()
    
    def execute_query(self, query: str, params: Optional[List] = None) -> pd.DataFrame:
        """
        执行自定义查询
        
        Args:
            query: SQL查询语句
            params: 查询参数
            
        Returns:
            DataFrame包含查询结果
        """
        try:
            if params:
                return self._conn.execute(query, params).fetchdf()
            else:
                return self._conn.execute(query).fetchdf()
                
        except Exception as e:
            logger.error(f"执行查询失败: {e}")
            return pd.DataFrame()
    
    def close(self):
        """关闭数据库连接并释放文件锁"""
        if self._conn:
            self._conn.close()
            self._conn = None
            logger.info("DuckDB连接已关闭")
        self._release_file_lock()
    
    def get_symbol_max_date(self, symbol: str) -> Optional[datetime.date]:
        """
        获取某只股票在数据库中的最新日期

        Args:
            symbol: 股票代码

        Returns:
            最新日期，如果没有数据返回 None
        """
        try:
            result = self._conn.execute(
                "SELECT MAX(date) FROM stock_daily WHERE symbol = ?",
                [symbol]
            ).fetchone()
            return result[0] if result and result[0] else None
        except Exception as e:
            logger.error(f"获取 {symbol} 最新日期失败: {e}")
            return None

    def get_symbols_with_date_range(self) -> pd.DataFrame:
        """
        获取所有已存储股票及其日期范围

        Returns:
            DataFrame，列: symbol, min_date, max_date, count
        """
        try:
            df = self._conn.execute("""
                SELECT
                    symbol,
                    MIN(date) AS min_date,
                    MAX(date) AS max_date,
                    COUNT(*) AS count
                FROM stock_daily
                GROUP BY symbol
                ORDER BY symbol
            """).fetchdf()
            return df
        except Exception as e:
            logger.error(f"获取股票日期范围失败: {e}")
            return pd.DataFrame()

    def save_trade_calendar(self, dates: List[str], exchange: str = 'SSE') -> bool:
        """
        保存交易日历

        Args:
            dates: 交易日列表 ['YYYYMMDD', ...]
            exchange: 交易所

        Returns:
            是否成功
        """
        try:
            if not dates:
                return False

            # 构建 DataFrame
            df_data = []
            for d in dates:
                normalized = self._normalize_date(d)
                if normalized:
                    df_data.append({'trade_date': normalized, 'exchange': exchange})

            if not df_data:
                return False

            df = pd.DataFrame(df_data)

            # 使用 INSERT OR REPLACE 避免重复
            self._conn.execute("""
                INSERT OR REPLACE INTO trade_calendar
                SELECT trade_date, exchange, CURRENT_TIMESTAMP FROM df
            """)

            logger.info(f"保存交易日历: {len(df)} 天")
            return True

        except Exception as e:
            logger.error(f"保存交易日历失败: {e}")
            return False

    def get_trade_calendar(self, start_date: Optional[str] = None,
                           end_date: Optional[str] = None) -> List[str]:
        """
        查询交易日历

        Args:
            start_date: 开始日期 (YYYYMMDD 或 YYYY-MM-DD)
            end_date: 结束日期

        Returns:
            交易日列表 ['YYYYMMDD', ...]
        """
        try:
            query = "SELECT trade_date FROM trade_calendar WHERE 1=1"
            params = []

            normalized_start = self._normalize_date(start_date)
            normalized_end = self._normalize_date(end_date)

            if normalized_start:
                query += " AND trade_date >= ?"
                params.append(normalized_start)
            if normalized_end:
                query += " AND trade_date <= ?"
                params.append(normalized_end)

            query += " ORDER BY trade_date"

            result = self._conn.execute(query, params).fetchall()
            dates = [row[0].strftime('%Y%m%d') if hasattr(row[0], 'strftime') else str(row[0]).replace('-', '') for row in result]
            return dates

        except Exception as e:
            logger.error(f"查询交易日历失败: {e}")
            return []

    def update_sync_status(self, status: str = 'idle', total_symbols: int = 0,
                           success_count: int = 0, failed_count: int = 0,
                           message: str = '') -> bool:
        """
        更新同步状态

        Args:
            status: 状态 (idle, running, completed, failed)
            total_symbols: 总股票数
            success_count: 成功数
            failed_count: 失败数
            message: 状态消息

        Returns:
            是否成功
        """
        try:
            self._conn.execute("""
                INSERT OR REPLACE INTO sync_status (id, last_sync_time, total_symbols,
                    success_count, failed_count, status, message, updated_at)
                VALUES (1, CURRENT_TIMESTAMP, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, [total_symbols, success_count, failed_count, status, message])
            return True
        except Exception as e:
            logger.error(f"更新同步状态失败: {e}")
            return False

    def get_sync_status(self) -> Optional[Dict[str, Any]]:
        """
        获取最近一次同步状态

        Returns:
            状态字典，如果没有则返回 None
        """
        try:
            result = self._conn.execute(
                "SELECT * FROM sync_status WHERE id = 1"
            ).fetchone()
            if result:
                columns = ['id', 'last_sync_time', 'total_symbols', 'success_count',
                           'failed_count', 'status', 'message', 'created_at', 'updated_at']
                return dict(zip(columns, result))
            return None
        except Exception as e:
            logger.error(f"获取同步状态失败: {e}")
            return None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
