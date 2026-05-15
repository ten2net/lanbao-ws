"""自选股管理 ROS2 节点"""
import os
import json
from typing import List, Dict

import rclpy
from rclpy.action import ActionServer
from rclpy.callback_groups import ReentrantCallbackGroup
from loguru import logger

from lanbao_core.base_node import LanBaoBaseNode
from lanbao_core.config import NodeConfig
from lanbao_interfaces.srv import FavorPick, FavorGetWatchlist, FavorManageCondition
from lanbao_interfaces.action import FavorRunSchedule
from lanbao_interfaces.msg import FavorPickResult, FavorWatchlistItem

from .duckdb_storage import FavorStorage
from .condition_manager import ConditionManager
from .stock_picker import StockPicker
from .favor_sync_manager import FavorSyncManager
from .schedule_manager import ScheduleManager
from .models import FavorCondition


class FavorNode(LanBaoBaseNode):
    def __init__(self):
        config = NodeConfig(node_name='favor_node', node_type='favor', publish_rate=0.1)
        super().__init__('favor_node', config)
        self._storage = None
        self._condition_mgr = None
        self._picker = None
        self._sync_mgr = None
        self._action_server = None
        self._pick_publisher = None

    def initialize(self) -> bool:
        try:
            self._storage = FavorStorage()
            self._condition_mgr = ConditionManager(self._storage)
            self._picker = StockPicker()

            try:
                self._sync_mgr = FavorSyncManager()
                logger.info("EastMoney 同步已初始化")
            except ValueError:
                logger.warning("EastMoney 凭证未配置，同步功能不可用")
                self._sync_mgr = None

            self._schedule_mgr = ScheduleManager(
                self,
                run_pick_callback=self._run_scheduled_pick,
                run_cleanup_callback=self._run_cleanup
            )

            self._setup_services()
            self._setup_action_server()
            self._setup_publisher()
            logger.info("FavorNode 初始化完成")
            return True
        except Exception as e:
            logger.exception(f"FavorNode 初始化失败: {e}")
            return False

    def _setup_services(self):
        self.create_service(FavorPick, '/favor/pick', self._handle_pick)
        self.create_service(FavorGetWatchlist, '/favor/get_watchlist', self._handle_get_watchlist)
        self.create_service(FavorManageCondition, '/favor/manage_condition', self._handle_manage_condition)
        logger.info("FavorNode Services 已注册")

    def _setup_action_server(self):
        self._action_server = ActionServer(
            self, FavorRunSchedule, '/favor/run_schedule',
            self._handle_run_schedule,
            callback_group=ReentrantCallbackGroup()
        )
        logger.info("FavorNode Action Server 已注册")

    def _setup_publisher(self):
        self._pick_publisher = self.create_publisher(
            FavorPickResult, '/favor/pick_result', self._qos_profiles['default']
        )

    def _handle_pick(self, request, response):
        try:
            condition_names = list(request.condition_names) if request.condition_names else []
            account_id = request.account_id or 'default'

            if condition_names:
                conditions = []
                for name in condition_names:
                    all_conditions = self._condition_mgr.list_conditions()
                    for c in all_conditions:
                        if c.name == name:
                            conditions.append(c)
                            break
            else:
                conditions = self._condition_mgr.get_enabled_conditions()

            results = self._picker.pick_multiple(conditions)

            all_codes = set()
            all_stocks = []
            for cond_name, stocks in results.items():
                for s in stocks:
                    if s.code not in all_codes:
                        all_codes.add(s.code)
                        all_stocks.append(s)

            added = 0
            existing = 0
            if self._sync_mgr:
                existing_list = self._sync_mgr.get_watchlist(group_name='自选股')
                existing_codes = {s['code'] for s in existing_list}

                if request.clear_existing and existing_codes:
                    self._sync_mgr.remove_stocks(list(existing_codes), group_name='自选股')
                    existing_codes = set()

                new_codes = [s.code for s in all_stocks if s.code not in existing_codes]
                if new_codes:
                    self._sync_mgr.add_stocks(new_codes, group_name='自选股')
                    added = len(new_codes)
                existing = len(all_codes) - added

            for cond_name, stocks in results.items():
                msg = FavorPickResult()
                msg.condition_name = cond_name
                msg.codes = [s.code for s in stocks]
                msg.count = len(stocks)
                msg.timestamp = str(self.get_clock().now().nanoseconds)
                self._pick_publisher.publish(msg)

            response.success = True
            response.message = "选股完成"
            response.total_unique = len(all_stocks)
            response.added = added
            response.existing = existing
            response.codes = list(all_codes)

        except Exception as e:
            logger.exception(f"选股失败: {e}")
            response.success = False
            response.message = str(e)

        return response

    def _handle_get_watchlist(self, request, response):
        try:
            items = self._storage.list_watchlist(
                account_id=request.account_id or None,
                group_name=request.group_name or None
            )
            response.success = True
            response.items = []
            for item in items:
                msg = FavorWatchlistItem()
                msg.code = item['code']
                msg.name = item.get('name', '')
                msg.account_id = item.get('account_id', 'default')
                msg.group_name = item.get('group_name', '自选股')
                msg.source_condition = item.get('source_condition', '')
                msg.signal_type = item.get('signal_type', '')
                msg.confidence = item.get('confidence', 0.0)
                msg.added_at = str(item.get('added_at', ''))
                response.items.append(msg)
        except Exception as e:
            logger.error(f"获取自选股失败: {e}")
            response.success = False
        return response

    def _handle_manage_condition(self, request, response):
        try:
            op = request.operation

            if op == 'list':
                conditions = self._condition_mgr.list_conditions()
                response.success = True
                response.conditions_json = json.dumps([c.model_dump() for c in conditions])

            elif op == 'get':
                cond = self._condition_mgr.get_condition(request.condition_id)
                response.success = cond is not None
                response.conditions_json = json.dumps(cond.model_dump() if cond else {})

            elif op == 'save':
                data = json.loads(request.condition_json)
                cond = FavorCondition(**data)
                cid = self._condition_mgr.save_condition(cond)
                response.success = True
                response.message = f"已保存 (id={cid})"

            elif op == 'delete':
                success = self._condition_mgr.delete_condition(request.condition_id)
                response.success = success
                response.message = "已删除" if success else "未找到"

            else:
                response.success = False
                response.message = f"未知操作: {op}"

        except Exception as e:
            logger.exception(f"条件管理失败: {e}")
            response.success = False
            response.message = str(e)

        return response

    def _handle_run_schedule(self, goal_handle):
        goal_handle.succeed()
        result = FavorRunSchedule.Result()
        result.success = True
        result.message = "定时任务执行完成"
        return result

    def start(self) -> bool:
        self._schedule_mgr.start()
        logger.info("FavorNode 启动")
        return True

    def stop(self):
        self._schedule_mgr.stop()
        logger.info("FavorNode 停止")
        if self._storage:
            self._storage.close()
        if self._action_server:
            self._action_server.destroy()

    def _run_scheduled_pick(self, schedule_name: str):
        logger.info(f"执行定时选股: {schedule_name}")
        conditions = self._condition_mgr.get_enabled_conditions()
        self._do_pick(conditions, clear_existing=False)

    def _run_cleanup(self, cleanup_type: str):
        logger.info(f"执行清理: {cleanup_type}")
        # TODO: implement cleanup logic (remove low volume stocks)


def main(args=None):
    rclpy.init(args=args)
    node = FavorNode()
    try:
        node.run()
    except KeyboardInterrupt:
        pass
    finally:
        node.shutdown()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
