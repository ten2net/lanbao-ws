"""
数据同步节点

负责从Tushare批量同步A股历史日线数据，支持增量更新。

特性:
- 交易日历感知：只下载实际交易日，跳过节假日
- 增量更新：查询每只股票最新日期，只下载缺失部分
- 后台执行：使用独立线程执行批量下载，不阻塞ROS2事件循环
- 定时调度：支持每日定时自动同步
- 进度追踪：定期报告同步进度和状态
"""

import os
import threading
import time
from datetime import datetime, timedelta, date
from typing import List, Dict, Optional, Any
from concurrent.futures import ThreadPoolExecutor, as_completed

import pandas as pd
import yaml
from loguru import logger

from lanbao_core.base_node import LanBaoBaseNode
from lanbao_core.config import NodeConfig
from std_msgs.msg import String as StdString

from lanbao_interfaces.srv import SaveResearchReport, GetResearchReport

from .tushare_adapter import TushareAdapter
from .duckdb_storage import DuckDBStorage


class DataSyncNode(LanBaoBaseNode):
    """
    数据同步节点

    批量从Tushare下载A股历史数据并保存到DuckDB，支持增量更新。
    """

    def __init__(self, config: Optional[NodeConfig] = None):
        super().__init__('data_sync_node', config)

        self._adapter: Optional[TushareAdapter] = None
        self._storage: Optional[DuckDBStorage] = None

        # 配置
        self._sync_enabled = True
        self._sync_start_date = '20200101'
        self._schedule_time = '17:00'
        self._run_on_startup = False
        self._batch_report_interval = 100
        self._max_workers = 1  # Tushare 100ms间隔，单线程约10 QPS

        # 运行状态
        self._sync_thread: Optional[threading.Thread] = None
        self._sync_running = False
        self._last_sync_time: Optional[datetime] = None
        self._sync_stats: Dict[str, Any] = {}

        # 定时器
        self._schedule_timer = None

        logger.info("DataSyncNode 初始化完成")

    def initialize(self) -> bool:
        """初始化节点资源（不持有长期数据库连接，避免与market_data_node冲突）"""
        try:
            # 加载配置
            self._load_config()

            # 初始化Tushare适配器
            self._adapter = TushareAdapter()

            # 注册健康检查
            self._health.register_check('tushare_connection', self._check_tushare, interval_seconds=60)
            self._health.register_check('storage_connection', self._check_storage_available, interval_seconds=60)

            # 创建研究报告相关服务
            self._save_research_report_service = self.create_service(
                SaveResearchReport,
                '/data_sync/save_research_report',
                self._handle_save_research_report
            )
            self._get_research_report_service = self.create_service(
                GetResearchReport,
                '/data_sync/get_research_report',
                self._handle_get_research_report
            )

            logger.info("DataSyncNode 资源初始化完成（无持久数据库连接）")
            return True

        except Exception as e:
            logger.error(f"DataSyncNode 初始化失败: {e}")
            return False

    def start(self) -> bool:
        """启动节点"""
        try:
            if not self._sync_enabled:
                logger.info("数据同步已禁用，节点处于待机状态")
                return True

            # 创建定时器，每分钟检查是否到达同步时间
            self._schedule_timer = self.create_timer(
                60.0,
                self._on_schedule_check,
                callback_group=self._callback_group
            )

            # 创建手动同步触发订阅
            self._sync_trigger_sub = self.create_subscription(
                StdString,
                '/data/trigger_sync',
                self._on_sync_trigger,
                10
            )
            logger.info("已注册手动同步触发订阅: /data/trigger_sync")

            # 启动时执行一次同步（如果配置启用）
            if self._run_on_startup:
                logger.info("配置为启动时立即执行同步")
                self._trigger_sync()
            else:
                # 检查今天是否已同步，若未同步且已过同步时间则补同步
                if self._should_sync_today():
                    logger.info(f"当前已过同步时间 {self._schedule_time}，今天尚未同步，立即补同步")
                    self._trigger_sync()
                else:
                    logger.info(f"数据同步节点已启动，将在每日 {self._schedule_time} 执行同步")

            return True

        except Exception as e:
            logger.error(f"DataSyncNode 启动失败: {e}")
            return False

    def stop(self):
        """停止节点"""
        try:
            # 等待后台同步线程结束
            if self._sync_thread and self._sync_thread.is_alive():
                logger.info("等待后台同步线程结束...")
                self._sync_running = False
                self._sync_thread.join(timeout=30)

            # 销毁定时器
            if self._schedule_timer:
                self.destroy_timer(self._schedule_timer)

            logger.info("DataSyncNode 已停止")

        except Exception as e:
            logger.error(f"DataSyncNode 停止时出错: {e}")

    def _load_config(self):
        """加载同步配置"""
        config_path = os.getenv('LANBAO_CONFIG', 'config/lanbao.yaml')

        if os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f)

                sync_config = config.get('data_sync', {})
                self._sync_enabled = sync_config.get('enabled', True)
                self._sync_start_date = sync_config.get('start_date', '20200101')
                self._schedule_time = sync_config.get('schedule_time', '17:00')
                self._run_on_startup = sync_config.get('run_on_startup', False)
                self._batch_report_interval = sync_config.get('batch_report_interval', 100)
                self._max_workers = sync_config.get('max_workers', 1)

                logger.info(f"加载同步配置: start_date={self._sync_start_date}, "
                           f"schedule={self._schedule_time}, enabled={self._sync_enabled}")

            except Exception as e:
                logger.warning(f"加载配置文件失败，使用默认配置: {e}")
        else:
            logger.warning(f"配置文件不存在: {config_path}，使用默认配置")

    def _should_sync_today(self) -> bool:
        """判断今天是否需要同步（已过同步时间且今天未同步）"""
        if not self._sync_enabled or self._sync_running:
            return False

        now = datetime.now()
        current_time = now.strftime('%H:%M')

        # 当前时间是否已过同步时间
        if current_time < self._schedule_time:
            return False

        # 今天是否已同步过
        if self._last_sync_time:
            last_date = self._last_sync_time.date()
            today = now.date()
            if last_date == today:
                return False

        return True

    def _on_schedule_check(self):
        """定时检查是否到达同步时间"""
        if not self._sync_enabled or self._sync_running:
            return

        now = datetime.now()
        current_time = now.strftime('%H:%M')

        # 检查是否到达设定的同步时间，或已过同步时间但今天未同步
        if current_time >= self._schedule_time:
            # 今天是否已同步过
            if self._last_sync_time:
                last_date = self._last_sync_time.date()
                today = now.date()
                if last_date == today:
                    return

            self._trigger_sync()

    def _on_sync_trigger(self, msg: StdString):
        """接收手动同步触发消息"""
        logger.info(f"收到手动同步触发请求: {msg.data}")
        self._trigger_sync()

    def _trigger_sync(self):
        """触发后台同步任务"""
        if self._sync_running:
            logger.warning("同步任务已在运行中，跳过本次触发")
            return

        self._sync_running = True
        self._last_sync_time = datetime.now()

        # 在后台线程中执行同步
        self._sync_thread = threading.Thread(target=self._sync_job, daemon=True)
        self._sync_thread.start()

        logger.info("后台同步任务已启动")

    def _sync_job(self):
        """
        执行数据同步任务（在后台线程中运行）
        同步时临时切换为写入模式，完成后恢复只读模式
        """
        start_time = time.time()
        total_symbols = 0
        success_count = 0
        failed_count = 0
        write_storage = None

        try:
            self._status.status = "SYNCING"

            # 步骤1: 获取全部A股列表（只读模式即可）
            logger.info("正在获取A股股票列表...")
            stock_list = self._adapter.get_stock_list(market='A')

            if stock_list.empty:
                logger.error("获取股票列表失败，同步终止")
                return

            total_symbols = len(stock_list)
            logger.info(f"获取到 {total_symbols} 只股票")

            # 步骤2: 计算增量更新范围（只读模式）
            logger.info("计算增量更新范围...")
            sync_tasks = self._build_sync_tasks(stock_list)
            logger.info(f"需要同步的股票: {len(sync_tasks)} 只")

            if not sync_tasks:
                logger.info("所有数据已是最新，无需同步")
                return

            # 步骤3: 关闭只读连接，获取写入连接
            logger.info("正在获取数据库写入权限...")
            db_path = os.getenv('DUCKDB_PATH', './data/lanbao.duckdb')

            # 关闭只读连接
            if self._storage:
                self._storage.close()
                self._storage = None

            # 等待其他进程释放锁（最多等待60秒）
            for attempt in range(60):
                try:
                    write_storage = DuckDBStorage(db_path, read_only=False)
                    logger.info("获取数据库写入权限成功")
                    break
                except Exception as e:
                    if attempt < 59:
                        logger.debug(f"等待数据库锁释放... ({attempt+1}/60)")
                        time.sleep(1)
                    else:
                        raise RuntimeError(f"无法获取数据库写入权限: {e}")

            if not write_storage:
                raise RuntimeError("无法获取数据库写入权限")

            # 步骤4: 更新交易日历（使用写入连接）
            self._update_trade_calendar(write_storage)

            # 步骤4b: 保存股票基本信息
            try:
                write_storage.save_stock_info(stock_list)
            except Exception as e:
                logger.warning(f"保存股票基本信息失败: {e}")

            # 步骤5: 执行批量下载和写入
            write_storage.update_sync_status(
                status='running',
                total_symbols=total_symbols,
                message=f'开始下载数据，共 {len(sync_tasks)} 只需同步'
            )

            if self._max_workers > 1:
                success_count, failed_count = self._download_parallel(sync_tasks, write_storage)
            else:
                success_count, failed_count = self._download_sequential(sync_tasks, write_storage)

            elapsed = time.time() - start_time
            message = (f"同步完成: 成功 {success_count}/{len(sync_tasks)}, "
                      f"失败 {failed_count}, 耗时 {elapsed:.1f}秒")
            logger.info(message)

            write_storage.update_sync_status(
                status='completed',
                total_symbols=total_symbols,
                success_count=success_count,
                failed_count=failed_count,
                message=message
            )

            self._publish_alert("INFO", message, component="data_sync")

        except Exception as e:
            elapsed = time.time() - start_time
            message = f"同步异常: {str(e)}, 耗时 {elapsed:.1f}秒"
            logger.error(message)

            if write_storage:
                write_storage.update_sync_status(
                    status='failed',
                    total_symbols=total_symbols,
                    success_count=success_count,
                    failed_count=failed_count,
                    message=message
                )

            self._publish_alert("ERROR", message, component="data_sync")

        finally:
            # 关闭写入连接
            if write_storage:
                write_storage.close()

            self._sync_running = False
            self._sync_stats = {
                'total': total_symbols,
                'synced': success_count,
                'failed': failed_count,
                'elapsed': time.time() - start_time,
                'last_sync': datetime.now().isoformat()
            }
            self._status.status = "RUNNING"

    def _update_trade_calendar(self, storage: DuckDBStorage):
        """更新交易日历（2020年至今）"""
        try:
            end_date = datetime.now().strftime('%Y%m%d')
            start_date = self._sync_start_date

            # 先从数据库查询已有的交易日历
            existing_dates = storage.get_trade_calendar(start_date, end_date)

            # 获取最新的交易日历
            tushare_dates = self._adapter.get_trade_calendar(start_date, end_date)

            if not tushare_dates:
                logger.warning("未能从Tushare获取交易日历")
                return

            # 找出新增的交易日
            new_dates = [d for d in tushare_dates if d not in existing_dates]

            if new_dates:
                storage.save_trade_calendar(new_dates)
                logger.info(f"交易日历更新: 新增 {len(new_dates)} 个交易日")
            else:
                logger.debug("交易日历已是最新")

        except Exception as e:
            logger.error(f"更新交易日历失败: {e}")

    def _build_sync_tasks(self, stock_list: pd.DataFrame) -> List[Dict[str, Any]]:
        """
        构建同步任务列表，计算每只股票需要下载的日期范围
        （临时创建只读连接，查询后立即关闭，避免与写入进程冲突）
        """
        tasks = []
        end_date = datetime.now().strftime('%Y%m%d')
        read_storage = None

        try:
            db_path = os.getenv('DUCKDB_PATH', './data/lanbao.duckdb')
            read_storage = DuckDBStorage(db_path, read_only=True)

            # 批量查询所有股票的数据范围
            db_range = read_storage.get_symbols_with_date_range()
            db_map = {}
            if not db_range.empty:
                db_map = dict(zip(db_range['symbol'], db_range['max_date']))

            for _, row in stock_list.iterrows():
                symbol = row['symbol']

                # 查询数据库最新日期
                max_date = db_map.get(symbol)

                if max_date is None:
                    # 全新股票，全量下载
                    tasks.append({
                        'symbol': symbol,
                        'start_date': self._sync_start_date,
                        'end_date': end_date,
                        'missing_days': 'all'
                    })
                else:
                    # 已有数据，计算增量
                    if isinstance(max_date, str):
                        max_date = datetime.strptime(max_date, '%Y-%m-%d').date()
                    elif hasattr(max_date, 'date'):
                        max_date = max_date.date() if hasattr(max_date, 'date') else max_date

                    # 计算下一个交易日
                    next_date = max_date + timedelta(days=1)
                    next_date_str = next_date.strftime('%Y%m%d')

                    # 查询需要补充的交易日
                    trade_dates = read_storage.get_trade_calendar(next_date_str, end_date)

                    if trade_dates:
                        tasks.append({
                            'symbol': symbol,
                            'start_date': next_date_str,
                            'end_date': end_date,
                            'missing_days': len(trade_dates)
                        })

        except Exception as e:
            logger.error(f"构建同步任务失败: {e}")
            # 如果无法读取数据库，假设所有股票都需要全量同步
            for _, row in stock_list.iterrows():
                tasks.append({
                    'symbol': row['symbol'],
                    'start_date': self._sync_start_date,
                    'end_date': end_date,
                    'missing_days': 'all (fallback)'
                })

        finally:
            if read_storage:
                read_storage.close()

        return tasks

    def _download_sequential(self, tasks: List[Dict[str, Any]], storage: DuckDBStorage) -> tuple:
        """顺序下载（单线程）"""
        success = 0
        failed = 0

        for i, task in enumerate(tasks):
            symbol = task['symbol']
            start_date = task['start_date']
            end_date = task['end_date']

            try:
                # 下载数据
                data = self._adapter.get_daily_data(symbol, start_date, end_date)

                if data.empty:
                    logger.warning(f"[{i+1}/{len(tasks)}] {symbol}: 未获取到数据")
                    failed += 1
                    continue

                # 保存到数据库
                if storage.save_daily_data(symbol, data):
                    success += 1
                else:
                    failed += 1

                # 定期报告进度
                if (i + 1) % self._batch_report_interval == 0:
                    progress = (i + 1) / len(tasks) * 100
                    logger.info(f"同步进度: {i+1}/{len(tasks)} ({progress:.1f}%)，"
                               f"成功 {success}，失败 {failed}")
                    storage.update_sync_status(
                        status='running',
                        success_count=success,
                        failed_count=failed,
                        message=f'进度 {progress:.1f}%'
                    )

            except Exception as e:
                logger.error(f"[{i+1}/{len(tasks)}] {symbol}: 下载失败 - {e}")
                failed += 1

        return success, failed

    def _download_parallel(self, tasks: List[Dict[str, Any]], storage: DuckDBStorage) -> tuple:
        """并行下载（多线程）"""
        success = 0
        failed = 0
        completed = 0
        lock = threading.Lock()

        def download_task(task: Dict[str, Any]) -> bool:
            nonlocal success, failed, completed
            symbol = task['symbol']
            start_date = task['start_date']
            end_date = task['end_date']

            try:
                data = self._adapter.get_daily_data(symbol, start_date, end_date)

                if data.empty:
                    with lock:
                        failed += 1
                        completed += 1
                    return False

                if storage.save_daily_data(symbol, data):
                    with lock:
                        success += 1
                        completed += 1
                    return True
                else:
                    with lock:
                        failed += 1
                        completed += 1
                    return False

            except Exception as e:
                logger.error(f"{symbol}: 下载失败 - {e}")
                with lock:
                    failed += 1
                    completed += 1
                return False

        with ThreadPoolExecutor(max_workers=self._max_workers) as executor:
            futures = {executor.submit(download_task, task): task for task in tasks}

            for future in as_completed(futures):
                completed += 0  # 实际计数在download_task中

                if completed % self._batch_report_interval == 0:
                    with lock:
                        progress = completed / len(tasks) * 100
                        logger.info(f"同步进度: {completed}/{len(tasks)} ({progress:.1f}%)，"
                                   f"成功 {success}，失败 {failed}")

        return success, failed

    def _check_tushare(self) -> Dict[str, Any]:
        """健康检查：Tushare连接"""
        if self._adapter and self._adapter.is_available():
            return {'status': 'HEALTHY', 'message': 'Tushare连接正常'}
        return {'status': 'UNHEALTHY', 'message': 'Tushare连接异常'}

    def _check_storage_available(self) -> Dict[str, Any]:
        """健康检查：存储是否可用（检查数据库文件是否存在，不建立连接）"""
        try:
            db_path = os.getenv('DUCKDB_PATH', './data/lanbao.duckdb')
            if os.path.exists(db_path):
                return {'status': 'HEALTHY', 'message': 'DuckDB数据库文件存在'}
            return {'status': 'DEGRADED', 'message': 'DuckDB数据库文件不存在，首次同步将创建'}
        except Exception as e:
            return {'status': 'UNHEALTHY', 'message': f'检查存储失败: {e}'}

    def _handle_save_research_report(self, request, response):
        """处理保存研究报告请求"""
        storage = None
        try:
            db_path = os.getenv('DUCKDB_PATH', './data/lanbao.duckdb')
            storage = DuckDBStorage(db_path, read_only=False)

            success = storage.save_research_report(
                report_id=request.report_id,
                report_type=request.report_type,
                symbols=list(request.symbols),
                summary=request.summary,
                verdict=request.verdict,
                confidence=request.confidence,
                report_json=request.report_json
            )

            response.success = success
            response.message = "保存成功" if success else "保存失败"
        except Exception as e:
            logger.error(f"保存研究报告服务出错: {e}")
            response.success = False
            response.message = f"保存失败: {str(e)}"
        finally:
            if storage:
                storage.close()

        return response

    def _handle_get_research_report(self, request, response):
        """处理获取研究报告请求"""
        storage = None
        try:
            db_path = os.getenv('DUCKDB_PATH', './data/lanbao.duckdb')
            storage = DuckDBStorage(db_path, read_only=True)

            report = storage.get_research_report(request.report_id)

            if report:
                response.found = True
                response.report_json = report.get('report_json', '')
                created_at = report.get('created_at')
                if created_at and hasattr(created_at, 'strftime'):
                    response.created_at = created_at.strftime('%Y-%m-%d %H:%M:%S')
                else:
                    response.created_at = str(created_at) if created_at else ''
            else:
                response.found = False
                response.report_json = ''
                response.created_at = ''
        except Exception as e:
            logger.error(f"获取研究报告服务出错: {e}")
            response.found = False
            response.report_json = ''
            response.created_at = ''
        finally:
            if storage:
                storage.close()

        return response


def main(args=None):
    """节点入口"""
    import rclpy
    rclpy.init(args=args)

    node = DataSyncNode()
    try:
        node.run()
    except KeyboardInterrupt:
        logger.info("收到中断信号")
    finally:
        node.shutdown()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
