"""
DuckDB 多进程并发锁

DuckDB 的存储格式限制：同一时间只能有一个进程打开数据库文件（即使是只读）。
通过操作系统文件锁（fcntl）协调多进程访问：
- 共享锁（SHARED）：允许多个读者并发
- 排他锁（EXCLUSIVE）：写者独占，阻塞所有读者

使用方式：
    with db_lock(db_path, mode='shared'):
        conn = duckdb.connect(db_path, read_only=True)
        ...
"""

import os
import time
import fcntl
from contextlib import contextmanager
from typing import Literal
from loguru import logger


@contextmanager
def db_lock(
    db_path: str,
    mode: Literal["shared", "exclusive"] = "shared",
    timeout: float = 60.0,
    poll_interval: float = 0.2,
):
    """
    DuckDB 文件锁上下文管理器

    Args:
        db_path: 数据库文件路径
        mode: 'shared' 共享锁（读）或 'exclusive' 排他锁（写）
        timeout: 获取锁的超时时间（秒）
        poll_interval: 轮询间隔（秒）

    Raises:
        TimeoutError: 超过 timeout 仍未获取到锁
    """
    lock_file = f"{db_path}.lock"
    fd = None
    lock_cmd = fcntl.LOCK_EX if mode == "exclusive" else fcntl.LOCK_SH

    try:
        fd = os.open(lock_file, os.O_CREAT | os.O_RDWR)
        start = time.time()
        acquired = False

        while time.time() - start < timeout:
            try:
                fcntl.flock(fd, lock_cmd | fcntl.LOCK_NB)
                acquired = True
                break
            except (IOError, OSError):
                time.sleep(poll_interval)

        if not acquired:
            raise TimeoutError(
                f"无法获取 DuckDB {mode} 锁，超时 {timeout}s"
            )

        logger.debug(f"获取 DuckDB {mode} 锁成功")
        yield

    finally:
        if fd is not None:
            try:
                fcntl.flock(fd, fcntl.LOCK_UN)
            except Exception:
                pass
            try:
                os.close(fd)
            except Exception:
                pass
            logger.debug(f"释放 DuckDB {mode} 锁")
