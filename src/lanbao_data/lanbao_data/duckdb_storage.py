"""
DuckDB数据存储模块
提供高性能的本地数据存储和查询
"""
import os
import duckdb
import pandas as pd
from datetime import datetime
from typing import Optional, List, Dict, Any
from pathlib import Path
from loguru import logger


class DuckDBStorage:
    """
    DuckDB存储管理器
    
    功能:
    - 股票数据存储
    - 高效查询
    - 数据缓存
    """
    
    def __init__(self, db_path: str = "./data/lanbao.duckdb"):
        """
        初始化DuckDB存储
        
        Args:
            db_path: 数据库文件路径
        """
        self._db_path = db_path
        
        # 确保目录存在
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        
        # 初始化连接
        self._conn = duckdb.connect(db_path)
        
        # 初始化表结构
        self._init_tables()
        
        logger.info(f"DuckDB存储初始化完成: {db_path}")
    
    def _init_tables(self):
        """初始化数据表"""
        # 股票日线数据表
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
        
        logger.debug("数据库表结构初始化完成")
    
    def save_daily_data(self, symbol: str, data: pd.DataFrame) -> bool:
        """
        保存日线数据
        
        Args:
            symbol: 股票代码
            data: DataFrame包含日线数据
            
        Returns:
            是否成功
        """
        try:
            if data.empty:
                return False
            
            # 准备数据
            df = data.copy()
            df['symbol'] = symbol
            
            # 确保列名正确
            required_cols = ['symbol', 'date', 'open', 'high', 'low', 'close', 'volume']
            for col in required_cols:
                if col not in df.columns:
                    logger.warning(f"数据缺少必要列: {col}")
                    return False
            
            # 删除已存在的数据(增量更新)
            dates = df['date'].tolist()
            if dates:
                date_str = ','.join([f"'{d}'" for d in dates])
                self._conn.execute(f"""
                    DELETE FROM stock_daily 
                    WHERE symbol = '{symbol}' AND date IN ({date_str})
                """)
            
            # 插入数据
            self._conn.execute("""
                INSERT INTO stock_daily 
                SELECT symbol, date, open, high, low, close, volume, amount, 
                       change_pct, data_source, CURRENT_TIMESTAMP
                FROM df
            """)
            
            logger.debug(f"保存 {symbol} 数据: {len(df)} 条")
            return True
            
        except Exception as e:
            logger.error(f"保存 {symbol} 数据失败: {e}")
            return False
    
    def get_daily_data(self, symbol: str, start_date: Optional[str] = None,
                       end_date: Optional[str] = None) -> pd.DataFrame:
        """
        获取日线数据
        
        Args:
            symbol: 股票代码
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            DataFrame包含日线数据
        """
        try:
            query = "SELECT * FROM stock_daily WHERE symbol = ?"
            params = [symbol]
            
            if start_date:
                query += " AND date >= ?"
                params.append(start_date)
            if end_date:
                query += " AND date <= ?"
                params.append(end_date)
            
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
            self._conn.execute("""
                INSERT OR REPLACE INTO backtest_results VALUES (
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP
                )
            """, [
                result['backtest_id'],
                result.get('strategy_id', ''),
                result.get('symbol', ''),
                result.get('start_date'),
                result.get('end_date'),
                result.get('total_return', 0),
                result.get('annual_return', 0),
                result.get('sharpe_ratio', 0),
                result.get('max_drawdown', 0),
                result.get('volatility', 0),
                result.get('win_rate', 0),
                result.get('trades_count', 0),
                str(result.get('params', {}))
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
        """关闭数据库连接"""
        if self._conn:
            self._conn.close()
            logger.info("DuckDB连接已关闭")
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
