"""WebSocket 进度桥接 — 连接前端 WebSocket 和 ROS2 Action Feedback"""
import time
from typing import Any, Callable, Dict, Optional

from fastapi import WebSocket
from loguru import logger


class BacktestProgressBridge:
    """管理 WebSocket 连接和 ROS2 Action Feedback 之间的映射"""

    def __init__(self):
        self._connections: Dict[str, WebSocket] = {}
        self._callbacks: Dict[str, Callable] = {}

    async def connect(self, task_id: str, websocket: WebSocket) -> None:
        """注册 WebSocket 连接"""
        await websocket.accept()
        self._connections[task_id] = websocket
        logger.info(f"WebSocket 已连接: {task_id}")

    async def disconnect(self, task_id: str) -> None:
        """注销 WebSocket 连接"""
        ws = self._connections.pop(task_id, None)
        if ws:
            try:
                await ws.close()
            except Exception:
                pass
        self._callbacks.pop(task_id, None)
        logger.info(f"WebSocket 已断开: {task_id}")

    def get_callback(self, task_id: str) -> Optional[Callable]:
        """获取指定任务的 Feedback 回调函数"""
        return self._callbacks.get(task_id)

    def register_callback(self, task_id: str, callback: Callable) -> None:
        """注册 Feedback 回调"""
        self._callbacks[task_id] = callback

    async def send_progress(
        self, task_id: str, progress: float, status: str
    ) -> None:
        """发送进度消息"""
        ws = self._connections.get(task_id)
        if ws is None:
            return
        try:
            await ws.send_json(
                {
                    "type": "progress",
                    "progress": round(progress, 2),
                    "status": status,
                    "timestamp": time.time(),
                }
            )
        except Exception as e:
            logger.warning(f"发送进度消息失败: {e}")

    async def send_completed(
        self, task_id: str, backtest_id: str, result: Optional[Dict] = None
    ) -> None:
        """发送完成消息"""
        ws = self._connections.get(task_id)
        if ws is None:
            return
        try:
            await ws.send_json(
                {
                    "type": "completed",
                    "backtest_id": backtest_id,
                    "result": result,
                    "timestamp": time.time(),
                }
            )
        except Exception as e:
            logger.warning(f"发送完成消息失败: {e}")

    async def send_error(self, task_id: str, message: str) -> None:
        """发送错误消息"""
        ws = self._connections.get(task_id)
        if ws is None:
            return
        try:
            await ws.send_json(
                {
                    "type": "error",
                    "message": message,
                    "timestamp": time.time(),
                }
            )
        except Exception as e:
            logger.warning(f"发送错误消息失败: {e}")


# 全局实例
progress_bridge = BacktestProgressBridge()
