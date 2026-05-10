"""JSON 文件存储服务 — 读写 reports/ 目录下的回测数据文件"""
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


def _get_reports_dir() -> Path:
    """获取报告目录（基于项目根目录）"""
    # 从当前文件向上回溯: api/services/ -> api/ -> lanbao_backtest/ -> src/ -> project_root/
    project_root = Path(__file__).parent.parent.parent.parent
    reports_dir = project_root / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    return reports_dir


class BacktestStorage:
    """回测结果存储服务"""

    def __init__(self):
        self._reports_dir = _get_reports_dir()

    def list_backtests(self) -> List[Dict[str, Any]]:
        """列出所有回测结果（只加载主 JSON 文件）"""
        results = []
        for f in sorted(self._reports_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
            # 跳过附属文件（如 .equity.json, .trades.json）
            if len(f.suffixes) > 1:
                continue
            try:
                with open(f, "r", encoding="utf-8") as fp:
                    data = json.load(fp)
                if isinstance(data, dict) and "backtest_id" in data:
                    results.append(data)
            except (json.JSONDecodeError, IOError):
                continue
        return results

    def get_backtest(self, backtest_id: str) -> Optional[Dict[str, Any]]:
        """获取单个回测主文件"""
        path = self._reports_dir / f"{backtest_id}.json"
        if not path.exists():
            return None
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def get_equity(self, backtest_id: str) -> Optional[List[Dict[str, Any]]]:
        """获取权益曲线"""
        path = self._reports_dir / f"{backtest_id}.equity.json"
        if not path.exists():
            return None
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("series")

    def get_trades(self, backtest_id: str) -> Optional[List[Dict[str, Any]]]:
        """获取交易明细"""
        path = self._reports_dir / f"{backtest_id}.trades.json"
        if not path.exists():
            return None
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("trades")

    def get_monthly(self, backtest_id: str) -> Optional[Dict[str, Dict[str, float]]]:
        """获取月度收益矩阵"""
        path = self._reports_dir / f"{backtest_id}.monthly.json"
        if not path.exists():
            return None
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("matrix")

    def save_backtest(self, backtest_id: str, data: Dict[str, Any]) -> None:
        """保存回测主文件"""
        path = self._reports_dir / f"{backtest_id}.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def delete_backtest(self, backtest_id: str) -> bool:
        """删除回测及其所有附属文件"""
        deleted = False
        for suffix in [".json", ".html", ".equity.json", ".trades.json", ".monthly.json"]:
            path = self._reports_dir / f"{backtest_id}{suffix}"
            if path.exists():
                path.unlink()
                deleted = True
        return deleted

    def update_tags(self, backtest_id: str, tags: List[str]) -> bool:
        """更新回测标签"""
        data = self.get_backtest(backtest_id)
        if data is None:
            return False
        data.setdefault("meta", {})
        data["meta"]["tags"] = tags
        self.save_backtest(backtest_id, data)
        return True


# 全局实例
storage = BacktestStorage()
