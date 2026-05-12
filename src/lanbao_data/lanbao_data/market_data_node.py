"""
市场数据节点 - ROS2节点实现

采用"按需连接"模式管理DuckDB：
- 初始化时不创建持久连接
- 每次查询/写入时临时创建连接，完成后立即关闭
- 避免长期持有数据库锁，与 data_sync_node 的批量同步兼容
"""
import os
from typing import Optional
import rclpy
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy
from loguru import logger
import pandas as pd
from datetime import datetime, timedelta
import json
from contextlib import contextmanager

from lanbao_core import DataProcessorNode, NodeConfig
from lanbao_interfaces.msg import MarketData, SystemAlert, DataStats, DataQualityItem, SyncStatusDetail, DataTable
from lanbao_interfaces.srv import GetMarketData, GetDataStats, GetDataQuality, GetSyncStatus, GetDataTables, GetTablePreview

from .tushare_adapter import TushareAdapter
from .tdx_adapter import TDXAdapter
from .akshare_adapter import AKShareAdapter
from .miniqmt_adapter import MiniQMTAdapter
from .duckdb_storage import DuckDBStorage


class MarketDataNode(DataProcessorNode):
    """
    市场数据节点

    职责:
    - 从多个数据源获取实时和历史数据（Tushare, 通达信, AkShare, MiniQMT）
    - 数据质量验证
    - 数据持久化到DuckDB
    - 通过ROS2发布数据
    """

    def __init__(self):
        config = NodeConfig(
            node_name='market_data_node',
            node_type='market_data',
            publish_rate=1.0
        )
        super().__init__('market_data_node', config)

        # 数据源适配器字典
        self._adapters = {}
        self._data_sources = []  # 按优先级排序的数据源列表

        # 数据缓存
        self._subscribed_symbols = set()
        self._last_data = {}

        # 数据库路径
        self._db_path = './data/lanbao.duckdb'

    @contextmanager
    def _db(self, read_only: bool = True, timeout: int = 30):
        """数据库连接上下文管理器 — 按需创建，用完即关"""
        storage = None
        try:
            storage = DuckDBStorage(self._db_path, read_only=read_only, timeout=timeout)
            yield storage
        finally:
            if storage:
                storage.close()

    def _setup_data_sources(self):
        """设置数据源"""
        data_source_config = os.getenv('LANBAO_DATA_SOURCES', 'tushare,akshare').lower()
        enabled_sources = [s.strip() for s in data_source_config.split(',')]

        logger.info(f"配置的数据源: {enabled_sources}")

        for source in enabled_sources:
            try:
                if source == 'tushare':
                    adapter = TushareAdapter()
                    if adapter.is_available():
                        self._adapters['tushare'] = adapter
                        logger.info("✓ Tushare数据源初始化成功")
                    else:
                        logger.warning("✗ Tushare数据源不可用")

                elif source == 'tdx':
                    adapter = TDXAdapter()
                    if adapter.is_available():
                        self._adapters['tdx'] = adapter
                        logger.info("✓ 通达信数据源初始化成功")
                    else:
                        logger.warning("✗ 通达信数据源不可用")

                elif source == 'akshare':
                    adapter = AKShareAdapter()
                    if adapter.is_available():
                        self._adapters['akshare'] = adapter
                        logger.info("✓ AkShare数据源初始化成功")
                    else:
                        logger.warning("✗ AkShare数据源不可用")

                elif source == 'miniqmt':
                    adapter = MiniQMTAdapter()
                    if adapter.is_available():
                        self._adapters['miniqmt'] = adapter
                        logger.info("✓ MiniQMT数据源初始化成功")
                    else:
                        logger.warning("✗ MiniQMT数据源不可用")

            except Exception as e:
                logger.error(f"初始化 {source} 数据源失败: {e}")

        self._data_sources = sorted(
            self._adapters.values(),
            key=lambda x: x.priority
        )

        if not self._data_sources:
            error_msg = "没有可用的数据源适配器"
            logger.error(error_msg)
            self._publish_alert("ERROR", error_msg)
        else:
            source_names = [type(s).__name__ for s in self._data_sources]
            logger.info(f"已启用的数据源（按优先级）: {source_names}")

    def initialize(self) -> bool:
        """初始化节点"""
        try:
            if not super().initialize():
                return False

            self._db_path = self._node_config.parameters.get('db_path', './data/lanbao.duckdb')

            # 验证数据库文件存在（不建立持久连接）
            if not os.path.exists(self._db_path):
                logger.warning(f"数据库文件不存在: {self._db_path}，首次查询时将创建")

            self._setup_services()

            self._data_timer = self.create_timer(
                60.0,
                self._update_data,
                callback_group=self._callback_group
            )

            logger.info("市场数据节点初始化完成（按需连接模式）")
            return True

        except Exception as e:
            logger.exception(f"市场数据节点初始化失败: {e}")
            return False

    def _setup_services(self):
        """设置ROS2服务"""
        self._get_data_service = self.create_service(
            GetMarketData,
            'market_data/get',
            self._handle_get_market_data,
            callback_group=self._callback_group
        )

        self._get_data_stats_service = self.create_service(
            GetDataStats,
            'data/stats',
            self._handle_get_data_stats,
            callback_group=self._callback_group
        )
        self._get_data_quality_service = self.create_service(
            GetDataQuality,
            'data/quality',
            self._handle_get_data_quality,
            callback_group=self._callback_group
        )
        self._get_sync_status_service = self.create_service(
            GetSyncStatus,
            'data/sync_status',
            self._handle_get_sync_status,
            callback_group=self._callback_group
        )
        self._get_data_tables_service = self.create_service(
            GetDataTables,
            'data/tables',
            self._handle_get_data_tables,
            callback_group=self._callback_group
        )
        self._get_table_preview_service = self.create_service(
            GetTablePreview,
            'data/preview',
            self._handle_get_table_preview,
            callback_group=self._callback_group
        )

        logger.info("市场数据服务已设置")

    def _handle_get_data_stats(self, request, response):
        """处理获取数据概况请求"""
        try:
            if not os.path.exists(self._db_path):
                response.success = False
                return response

            with self._db(read_only=True) as storage:
                conn = storage._conn
                total_records = conn.execute("SELECT COUNT(*) FROM stock_daily").fetchone()[0]
                total_symbols = conn.execute("SELECT COUNT(DISTINCT symbol) FROM stock_daily").fetchone()[0]
                date_range = conn.execute("SELECT MIN(date), MAX(date) FROM stock_daily").fetchone()
                db_size_mb = os.path.getsize(self._db_path) / (1024 * 1024)
                exchanges = conn.execute(
                    "SELECT SUBSTR(symbol, 1, 2) as prefix, COUNT(DISTINCT symbol) as cnt "
                    "FROM stock_daily GROUP BY prefix ORDER BY cnt DESC"
                ).fetchall()

                # 计算覆盖天数
                coverage_days = 0
                if date_range[0] and date_range[1]:
                    try:
                        d1 = datetime.strptime(str(date_range[0]), "%Y-%m-%d")
                        d2 = datetime.strptime(str(date_range[1]), "%Y-%m-%d")
                        coverage_days = (d2 - d1).days + 1
                    except Exception:
                        pass

                # 获取最后同步时间
                sync_result = conn.execute(
                    "SELECT last_sync_time FROM sync_status WHERE id = 1"
                ).fetchone()
                last_sync = str(sync_result[0]) if sync_result and sync_result[0] else ""

            exchange_names = []
            exchange_counts = []
            prefix_map = {'60': '上海主板', '68': '科创板', '00': '深圳主板', '30': '创业板', '92': '北交所'}
            for prefix, cnt in exchanges:
                exchange_names.append(prefix_map.get(prefix, prefix))
                exchange_counts.append(cnt)

            stats = DataStats()
            stats.total_records = int(total_records)
            stats.total_symbols = int(total_symbols)
            stats.start_date = str(date_range[0]) if date_range[0] else ""
            stats.end_date = str(date_range[1]) if date_range[1] else ""
            stats.db_size_mb = round(db_size_mb, 2)
            stats.exchange_names = exchange_names
            stats.exchange_counts = exchange_counts
            stats.coverage_days = coverage_days
            stats.last_sync_time = last_sync
            stats.total_daily_records = int(total_records)

            response.stats = stats
            response.success = True

        except Exception as e:
            logger.error(f"获取数据概况失败: {e}")
            response.success = False
        return response

    def _handle_get_data_tables(self, request, response):
        """处理获取数据表列表请求"""
        try:
            tables = []
            with self._db(read_only=True) as storage:
                conn = storage._conn
                table_rows = conn.execute(
                    "SELECT table_name FROM information_schema.tables WHERE table_schema = 'main'"
                ).fetchall()

                for (table_name,) in table_rows:
                    try:
                        count_result = conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()
                        record_count = count_result[0] if count_result else 0

                        date_start = None
                        date_end = None
                        try:
                            cols = conn.execute(
                                f"SELECT column_name FROM information_schema.columns WHERE table_name = '{table_name}'"
                            ).fetchall()
                            col_names = [c[0] for c in cols]
                            if "date" in col_names:
                                range_result = conn.execute(
                                    f"SELECT MIN(date), MAX(date) FROM {table_name}"
                                ).fetchone()
                                date_start = str(range_result[0]) if range_result and range_result[0] else ""
                                date_end = str(range_result[1]) if range_result and range_result[1] else ""
                        except Exception:
                            pass

                        quality_score = 100.0
                        if record_count > 0:
                            try:
                                cols = conn.execute(
                                    f"SELECT column_name FROM information_schema.columns WHERE table_name = '{table_name}'"
                                ).fetchall()
                                null_counts = []
                                for (col_name,) in cols:
                                    if col_name in ("created_at", "updated_at", "data_source"):
                                        continue
                                    try:
                                        null_result = conn.execute(
                                            f"SELECT COUNT(*) FROM {table_name} WHERE {col_name} IS NULL"
                                        ).fetchone()
                                        null_counts.append(null_result[0])
                                    except Exception:
                                        pass
                                total_nulls = sum(null_counts)
                                if total_nulls > 0:
                                    quality_score = max(0.0, 100.0 - (total_nulls / record_count) * 100)
                            except Exception:
                                pass

                        table = DataTable()
                        table.name = table_name
                        table.record_count = int(record_count)
                        table.date_start = date_start or ""
                        table.date_end = date_end or ""
                        table.quality_score = round(quality_score, 1)
                        tables.append(table)
                    except Exception as e:
                        logger.warning(f"处理表 {table_name} 失败: {e}")

            response.tables = tables
            response.success = True

        except Exception as e:
            logger.error(f"获取数据表列表失败: {e}")
            response.success = False
        return response

    def _handle_get_table_preview(self, request, response):
        """处理获取表预览数据请求"""
        try:
            table_name = request.table_name
            limit = request.limit if request.limit > 0 else 100

            with self._db(read_only=True) as storage:
                conn = storage._conn

                # 验证表存在
                tables = conn.execute(
                    "SELECT table_name FROM information_schema.tables WHERE table_schema = 'main'"
                ).fetchall()
                if table_name not in [t[0] for t in tables]:
                    response.success = True
                    response.json_data = json.dumps({"table": table_name, "columns": [], "rows": [], "total": 0, "limit": limit})
                    return response

                # 获取列信息
                cols = conn.execute(
                    "SELECT column_name, data_type FROM information_schema.columns "
                    f"WHERE table_name = '{table_name}' ORDER BY ordinal_position"
                ).fetchall()
                columns = [{"name": c[0], "type": c[1] or "UNKNOWN"} for c in cols]

                # 获取总行数
                count_result = conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()
                total = count_result[0] if count_result else 0

                # 获取前 N 行
                rows = conn.execute(f"SELECT * FROM {table_name} LIMIT {limit}").fetchall()

                # 序列化
                serializable_rows = []
                for row in rows:
                    new_row = []
                    for val in row:
                        if val is None:
                            new_row.append(None)
                        elif hasattr(val, "isoformat"):
                            new_row.append(val.isoformat())
                        elif hasattr(val, "__float__"):
                            new_row.append(float(val))
                        elif hasattr(val, "__int__") and not isinstance(val, bool):
                            new_row.append(int(val))
                        else:
                            new_row.append(val)
                    serializable_rows.append(new_row)

                result = {
                    "table": table_name,
                    "columns": columns,
                    "rows": serializable_rows,
                    "total": total,
                    "limit": limit,
                }
                response.json_data = json.dumps(result)
                response.success = True

        except Exception as e:
            logger.error(f"预览表 {request.table_name} 失败: {e}")
            response.success = False
            response.json_data = json.dumps({"error": str(e)})
        return response

    def _handle_get_data_quality(self, request, response):
        """处理获取数据质量请求"""
        try:
            with self._db(read_only=True) as storage:
                conn = storage._conn
                total = conn.execute("SELECT COUNT(*) FROM stock_daily").fetchone()[0]
                if total == 0:
                    response.success = True
                    response.items = []
                    return response

                checks = [
                    ('空值检测', "SELECT COUNT(*) FROM stock_daily WHERE open IS NULL OR high IS NULL OR low IS NULL OR close IS NULL OR volume IS NULL", '个'),
                    ('零价格', "SELECT COUNT(*) FROM stock_daily WHERE open = 0 OR high = 0 OR low = 0 OR close = 0", '条'),
                    ('负价格', "SELECT COUNT(*) FROM stock_daily WHERE open < 0 OR high < 0 OR low < 0 OR close < 0", '条'),
                    ('high < low', "SELECT COUNT(*) FROM stock_daily WHERE high < low", '条'),
                    ('价格越界', "SELECT COUNT(*) FROM stock_daily WHERE close > high OR close < low", '条'),
                    ('重复记录', "SELECT COUNT(*) - COUNT(DISTINCT symbol || '_' || date) FROM stock_daily", '条'),
                    ('零成交量', "SELECT COUNT(*) FROM stock_daily WHERE volume = 0", '条'),
                    ('复权因子默认值', "SELECT COUNT(*) FROM stock_daily WHERE adj_factor = 1.0", '条'),
                ]

                items = []
                for name, sql, unit in checks:
                    fail_count = conn.execute(sql).fetchone()[0]
                    item = DataQualityItem()
                    item.check_name = name
                    item.fail_count = int(fail_count)
                    item.pass_count = int(total - fail_count)
                    if fail_count == 0:
                        item.status = "PASS"
                        item.description = "全部通过"
                    elif name == '复权因子默认值':
                        pct = fail_count / total * 100
                        item.status = "WARNING" if pct < 10 else "FAIL"
                        item.description = f"{fail_count} 条 ({pct:.1f}%)"
                    else:
                        item.status = "FAIL"
                        item.description = f"{fail_count} {unit}"
                    items.append(item)

            response.items = items
            response.success = True

        except Exception as e:
            logger.error(f"获取数据质量失败: {e}")
            response.success = False
        return response

    def _handle_get_sync_status(self, request, response):
        """处理获取同步状态请求"""
        try:
            with self._db(read_only=True) as storage:
                conn = storage._conn
                result = conn.execute("SELECT * FROM sync_status WHERE id = 1 LIMIT 1").fetchone()
                if result:
                    detail = SyncStatusDetail()
                    detail.status = str(result[5]) if result[5] else "unknown"
                    detail.last_sync_time = str(result[1]) if result[1] else ""
                    detail.total_symbols = int(result[2]) if result[2] else 0
                    detail.success_count = int(result[3]) if result[3] else 0
                    detail.failed_count = int(result[4]) if result[4] else 0
                    detail.duration_seconds = 0.0
                    detail.message = str(result[6]) if result[6] else ""
                    response.detail = detail
                    response.success = True
                else:
                    response.success = True
                    detail = SyncStatusDetail()
                    detail.status = "unknown"
                    detail.message = "暂无同步记录"
                    response.detail = detail

        except Exception as e:
            logger.error(f"获取同步状态失败: {e}")
            response.success = False
        return response

    def _get_data_from_source(self, symbol: str, start_date: Optional[str],
                               end_date: Optional[str]) -> pd.DataFrame:
        """从数据源获取数据，支持fallback机制"""
        # 先从本地存储查询
        with self._db(read_only=True) as storage:
            data = storage.get_daily_data(symbol, start_date, end_date)

        if not data.empty:
            logger.debug(f"从本地缓存获取 {symbol} 数据: {len(data)} 条")
            return data

        # 本地数据不完整，从远程数据源获取
        for adapter in self._data_sources:
            source_name = type(adapter).__name__
            try:
                logger.info(f"尝试从 {source_name} 获取 {symbol} 数据")
                data = adapter.get_daily_data(symbol, start_date, end_date)

                if not data.empty:
                    self._save_daily_data(symbol, data)
                    logger.info(f"✓ 从 {source_name} 成功获取 {len(data)} 条数据")
                    return data
                else:
                    logger.warning(f"✗ {source_name} 返回空数据")

            except Exception as e:
                logger.warning(f"✗ 从 {source_name} 获取数据失败: {e}")
                continue

        return pd.DataFrame()

    def _handle_get_market_data(self, request, response):
        """处理获取市场数据请求"""
        try:
            symbol = request.symbol
            start_date = request.start_date if request.start_date else None
            end_date = request.end_date if request.end_date else None

            logger.info(f"收到数据请求: {symbol} [{start_date} ~ {end_date}]")

            data = self._get_data_from_source(symbol, start_date, end_date)

            if data.empty:
                response.success = False
                response.message = f"未找到 {symbol} 的数据"
                return response

            response.data = []
            for _, row in data.iterrows():
                msg = MarketData()
                msg.header.stamp = self.get_clock().now().to_msg()
                msg.symbol = symbol
                msg.open = float(row['open'])
                msg.high = float(row['high'])
                msg.low = float(row['low'])
                msg.close = float(row['close'])
                msg.volume = float(row['volume'])
                msg.amount = float(row.get('amount', 0))
                msg.data_source = row.get('data_source', 'unknown')
                msg.timestamp = int(row['date'].timestamp() * 1000) if hasattr(row['date'], 'timestamp') else 0
                response.data.append(msg)

            response.success = True
            response.message = f"成功获取 {len(response.data)} 条数据"
            logger.info(f"返回 {len(response.data)} 条数据")

        except Exception as e:
            logger.error(f"处理数据请求失败: {e}")
            response.success = False
            response.message = f"处理失败: {str(e)}"

        return response

    def _update_data(self):
        """定时更新数据"""
        try:
            if not self._subscribed_symbols:
                return

            for symbol in self._subscribed_symbols:
                self._refresh_symbol_data(symbol)

        except Exception as e:
            logger.error(f"更新数据失败: {e}")

    def _refresh_symbol_data(self, symbol: str):
        """刷新股票数据"""
        try:
            today = datetime.now().strftime('%Y%m%d')

            for adapter in self._data_sources:
                try:
                    data = adapter.get_daily_data(symbol, today, today)

                    if not data.empty:
                        self._save_daily_data(symbol, data)
                        self._last_data[symbol] = data.iloc[-1].to_dict()
                        logger.debug(f"刷新 {symbol} 数据完成 ({type(adapter).__name__})")
                        return

                except Exception as e:
                    logger.warning(f"从 {type(adapter).__name__} 刷新 {symbol} 数据失败: {e}")
                    continue

        except Exception as e:
            logger.error(f"刷新 {symbol} 数据失败: {e}")

    def process_data(self, data):
        """处理数据 - 实现基类方法"""
        quality_report = self.validate_quality(data)

        if not quality_report['valid']:
            logger.warning(f"数据质量检查未通过: {quality_report['issues']}")
            return None

        return data

    def _save_daily_data(self, symbol: str, data: pd.DataFrame):
        """使用临时写连接保存数据"""
        try:
            with self._db(read_only=False, timeout=60) as storage:
                storage.save_daily_data(symbol, data)
                logger.debug(f"已缓存 {symbol} 数据到本地")
        except Exception as e:
            logger.warning(f"缓存 {symbol} 数据失败: {e}")

    def start(self) -> bool:
        """启动节点"""
        try:
            logger.info("市场数据节点启动完成")
            return True
        except Exception as e:
            logger.error(f"启动失败: {e}")
            return False

    def stop(self):
        """停止节点"""
        logger.info("市场数据节点已停止")

    def subscribe_symbol(self, symbol: str):
        """订阅股票"""
        self._subscribed_symbols.add(symbol)
        logger.info(f"订阅股票: {symbol}")

    def unsubscribe_symbol(self, symbol: str):
        """取消订阅"""
        self._subscribed_symbols.discard(symbol)
        logger.info(f"取消订阅股票: {symbol}")


def main(args=None):
    """节点入口函数"""
    rclpy.init(args=args)

    node = MarketDataNode()

    try:
        node.run()
    except KeyboardInterrupt:
        logger.info("收到中断信号")
    finally:
        node.shutdown()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
