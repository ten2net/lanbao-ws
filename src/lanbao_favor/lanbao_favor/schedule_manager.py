"""定时任务调度器 - 使用 ROS2 Timer"""
from typing import Dict, Callable
from datetime import datetime, time, timedelta

from loguru import logger


class ScheduleManager:
    """管理定时选股和清理任务"""

    SCHEDULES = {
        "pre_market": {"hour": 9, "minute": 0, "description": "开盘前预热"},
        "morning": {"hour": 10, "minute": 30, "description": "早盘选股"},
        "afternoon": {"hour": 14, "minute": 0, "description": "午盘选股"},
        "pre_close": {"hour": 14, "minute": 50, "description": "收盘前整理"},
        "post_market": {"hour": 15, "minute": 30, "description": "盘后选股"},
        "cleanup_volume": {"hour": 15, "minute": 35, "description": "清理低成交额"},
    }

    def __init__(self, node, run_pick_callback: Callable, run_cleanup_callback: Callable):
        self._node = node
        self._run_pick = run_pick_callback
        self._run_cleanup = run_cleanup_callback
        self._timers = []

    def start(self):
        """启动所有定时器"""
        logger.info("ScheduleManager 启动")
        for name, spec in self.SCHEDULES.items():
            timer = self._create_daily_timer(name, spec)
            self._timers.append((name, timer))

    def stop(self):
        """停止所有定时器"""
        for name, timer in self._timers:
            timer.cancel()
        self._timers.clear()
        logger.info("ScheduleManager 停止")

    def _create_daily_timer(self, name: str, spec: Dict):
        """创建每日定时器"""
        hour = spec["hour"]
        minute = spec["minute"]

        now = datetime.now()
        target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if target <= now:
            target += timedelta(days=1)

        interval_sec = (target - now).total_seconds()

        def callback():
            logger.info(f"定时任务触发: {name}")
            if "cleanup" in name:
                self._run_cleanup(name)
            else:
                self._run_pick(name)
            # Re-schedule for next day
            self._create_daily_timer(name, spec)

        timer = self._node.create_timer(interval_sec, callback)
        logger.info(f"定时任务已注册: {name} @ {hour:02d}:{minute:02d}")
        return timer
