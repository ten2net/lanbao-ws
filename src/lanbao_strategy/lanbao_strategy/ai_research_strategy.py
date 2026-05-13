"""
AI 投研策略

将 AI 投研报告（ResearchReport）转换为交易信号。
通过注入的 report_provider 获取报告，支持降级和过期衰减机制。
"""
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime, timedelta
import pandas as pd
from loguru import logger

from .strategy_template import StrategyTemplate, Signal, StrategyParams


class AIResearchStrategy(StrategyTemplate):
    """
    AI 投研策略

    将 AI 投研报告中的评级和置信度转换为标准交易信号。

    工作流程：
    1. 通过 report_provider 获取指定股票的最新投研报告
    2. 从报告中提取该股票的 synthesis.verdict 和 confidence
    3. 映射为交易信号（BUY/SELL/HOLD）和强度
    4. 检查报告是否过期，过期则衰减信号强度

    降级机制：
    - 获取超时 → HOLD 信号
    - 报告过期（默认 > 24 小时）→ 信号强度按时间衰减
    - 无报告 → HOLD 信号
    """

    # Verdict 到交易信号的映射
    VERDICT_SIGNAL_MAP = {
        "STRONG_BUY": ("BUY", 1.0),
        "BUY": ("BUY", 0.7),
        "HOLD": ("HOLD", 0.0),
        "SELL": ("SELL", 0.7),
        "STRONG_SELL": ("SELL", 1.0),
    }

    def __init__(
        self,
        strategy_id: str,
        name: str = "AI投研策略",
        symbol: str = "",
        report_provider: Optional[Callable[[str], Optional[Any]]] = None,
        refresh_interval: int = 1,
        expiry_hours: float = 24.0,
        params: Optional[StrategyParams] = None,
    ):
        """
        初始化 AI 投研策略

        Args:
            strategy_id: 策略ID
            name: 策略名称
            symbol: 监控的股票代码
            report_provider: 报告获取回调，接收 symbol，返回 ResearchReport 或 dict
            refresh_interval: 刷新间隔（K线数），默认每 1 根K线检查
            expiry_hours: 报告过期时间（小时），默认 24 小时
            params: 策略参数
        """
        super().__init__(strategy_id, name, params)

        self._symbol = symbol
        self._report_provider = report_provider
        self._refresh_interval = refresh_interval
        self._expiry_hours = expiry_hours

        # 缓存
        self._cached_report: Optional[Any] = None
        self._cached_at: Optional[datetime] = None
        self._data_count: int = 0  # K线计数

    @property
    def symbol(self) -> str:
        """获取监控的股票代码"""
        return self._symbol

    def set_report_provider(self, provider: Callable[[str], Optional[Any]]):
        """
        设置报告获取回调

        Args:
            provider: 接收 symbol，返回 ResearchReport/dict/None 的回调
        """
        self._report_provider = provider

    def _should_refresh(self) -> bool:
        """是否应刷新报告"""
        self._data_count += 1
        return self._data_count % self._refresh_interval == 0

    def _fetch_report(self, symbol: str) -> Optional[Any]:
        """
        获取投研报告

        Args:
            symbol: 股票代码

        Returns:
            报告对象或 None
        """
        if self._report_provider is None:
            logger.warning(f"[{self._strategy_id}] 未设置 report_provider")
            return None

        try:
            report = self._report_provider(symbol)
            self._cached_report = report
            self._cached_at = datetime.now()
            return report
        except Exception as e:
            logger.error(f"[{self._strategy_id}] 获取投研报告失败: {e}")
            return None

    def _get_cached_or_fetch(self, symbol: str) -> Optional[Any]:
        """获取缓存的报告，或触发刷新"""
        if self._cached_report is None or self._should_refresh():
            return self._fetch_report(symbol)
        return self._cached_report

    def _extract_verdict_from_report(
        self, report: Any, symbol: str
    ) -> tuple[Optional[str], Optional[float], Optional[int], Optional[str]]:
        """
        从报告中提取指定股票的评级信息

        Returns:
            (verdict, confidence, score, report_time)
        """
        # 支持 Pydantic 模型和字典两种格式
        if hasattr(report, "model_dump"):
            data = report.model_dump()
        elif hasattr(report, "to_dict"):
            data = report.to_dict()
        else:
            data = report if isinstance(report, dict) else {}

        # 提取报告时间
        report_time = data.get("created_at", "")

        # 查找指定股票的 analysis
        stock_analyses = data.get("stock_analyses", [])
        for stock in stock_analyses:
            stock_symbol = stock.get("symbol", "") if isinstance(stock, dict) else getattr(stock, "symbol", "")
            if stock_symbol == symbol:
                # 优先使用 synthesis 的综合评级
                synthesis = stock.get("synthesis") if isinstance(stock, dict) else getattr(stock, "synthesis", None)
                if synthesis:
                    if isinstance(synthesis, dict):
                        verdict = synthesis.get("verdict", "HOLD")
                        score = synthesis.get("score", 50)
                    else:
                        verdict = getattr(synthesis, "verdict", "HOLD")
                        score = getattr(synthesis, "score", 50)
                else:
                    # fallback: 取 fundamental/technical/sentiment 的加权平均
                    verdict = self._aggregate_verdicts(stock)
                    score = self._aggregate_score(stock)

                # 统一转换为字符串（处理 Pydantic Enum，如 Verdict.BUY）
                if hasattr(verdict, "value"):
                    verdict = verdict.value
                else:
                    verdict = str(verdict)

                # 从 summary 获取整体置信度
                summary = data.get("summary", {})
                if isinstance(summary, dict):
                    confidence = summary.get("confidence", 0.5)
                else:
                    confidence = getattr(summary, "confidence", 0.5)

                return str(verdict), float(confidence), int(score), report_time

        # 如果找不到个股分析，尝试从 summary 获取整体评级
        summary = data.get("summary", {})
        if isinstance(summary, dict):
            return (
                summary.get("overall_verdict", "HOLD"),
                summary.get("confidence", 0.5),
                50,
                report_time,
            )

        return None, None, None, report_time

    def _aggregate_verdicts(self, stock: Any) -> str:
        """
        聚合多维度评级为单一评级
        简单规则：如果有任一维度为 STRONG_BUY/STRONG_SELL 则采用，否则多数决
        """
        if not isinstance(stock, dict):
            return "HOLD"

        verdicts = []
        for key in ["fundamental", "technical", "sentiment"]:
            section = stock.get(key)
            if section:
                v = section.get("verdict", "HOLD") if isinstance(section, dict) else getattr(section, "verdict", "HOLD")
                verdicts.append(str(v))

        if not verdicts:
            return "HOLD"

        # 优先级：STRONG_BUY > BUY > HOLD > SELL > STRONG_SELL
        priority = {"STRONG_BUY": 2, "BUY": 1, "HOLD": 0, "SELL": -1, "STRONG_SELL": -2}
        scores = [priority.get(v, 0) for v in verdicts]
        avg_score = sum(scores) / len(scores)

        if avg_score >= 1.5:
            return "STRONG_BUY"
        elif avg_score >= 0.5:
            return "BUY"
        elif avg_score <= -1.5:
            return "STRONG_SELL"
        elif avg_score <= -0.5:
            return "SELL"
        return "HOLD"

    def _aggregate_score(self, stock: Any) -> int:
        """聚合多维度评分"""
        if not isinstance(stock, dict):
            return 50

        scores = []
        for key in ["fundamental", "technical", "sentiment"]:
            section = stock.get(key)
            if section:
                s = section.get("score", 50) if isinstance(section, dict) else getattr(section, "score", 50)
                scores.append(int(s))

        return int(sum(scores) / len(scores)) if scores else 50

    def _calculate_decay_factor(self, report_time_str: str) -> float:
        """
        计算信号衰减因子

        报告越旧，衰减越严重。过期后线性衰减至 0。
        """
        if not report_time_str:
            return 1.0

        try:
            # 尝试多种时间格式
            for fmt in ["%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%d %H:%M:%S"]:
                try:
                    report_time = datetime.strptime(report_time_str[:19], fmt)
                    break
                except ValueError:
                    continue
            else:
                return 1.0
        except Exception:
            return 1.0

        elapsed = datetime.now() - report_time
        expiry = timedelta(hours=self._expiry_hours)

        if elapsed <= timedelta(0):
            return 1.0
        if elapsed >= expiry:
            return 0.0

        # 线性衰减
        return 1.0 - (elapsed.total_seconds() / expiry.total_seconds())

    def _verdict_to_signal(
        self,
        verdict: str,
        confidence: float,
        score: int,
        decay_factor: float,
    ) -> Signal:
        """
        将评级转换为交易信号

        Args:
            verdict: 评级字符串
            confidence: 置信度 0-1
            score: 评分 0-100
            decay_factor: 衰减因子 0-1

        Returns:
            Signal 对象
        """
        action, base_strength = self.VERDICT_SIGNAL_MAP.get(verdict, ("HOLD", 0.0))

        if action == "HOLD":
            return Signal(
                symbol=self._symbol,
                action="HOLD",
                strength=0.0,
                reason=f"AI评级: {verdict}，无交易信号",
                params={"verdict": verdict, "score": score},
            )

        # 信号强度公式
        strength = base_strength * confidence * (score / 100.0) * decay_factor
        strength = min(max(strength, 0.0), 1.0)

        if decay_factor < 1.0:
            reason = (
                f"AI评级: {verdict} (置信度 {confidence:.0%}, 得分 {score}), "
                f"信号已衰减 {decay_factor:.0%}"
            )
        else:
            reason = f"AI评级: {verdict} (置信度 {confidence:.0%}, 得分 {score})"

        return Signal(
            symbol=self._symbol,
            action=action,
            strength=strength,
            reason=reason,
            params={
                "verdict": verdict,
                "confidence": round(confidence, 4),
                "score": score,
                "decay_factor": round(decay_factor, 4),
                "base_strength": base_strength,
            },
        )

    def analyze(self, data: pd.DataFrame) -> Dict[str, Any]:
        """
        分析投研报告

        Args:
            data: 市场数据（用于提取 symbol）

        Returns:
            分析结果字典
        """
        symbol = self._extract_symbol(data) or self._symbol

        report = self._get_cached_or_fetch(symbol)
        if report is None:
            return {
                "symbol": symbol,
                "has_report": False,
                "verdict": None,
                "error": "无法获取投研报告",
            }

        verdict, confidence, score, report_time = self._extract_verdict_from_report(
            report, symbol
        )
        decay_factor = self._calculate_decay_factor(report_time or "")

        return {
            "symbol": symbol,
            "has_report": True,
            "verdict": verdict,
            "confidence": confidence,
            "score": score,
            "report_time": report_time,
            "decay_factor": decay_factor,
        }

    def generate_signals(self, data: pd.DataFrame) -> List[Signal]:
        """
        生成交易信号

        Args:
            data: 市场数据

        Returns:
            信号列表（0 或 1 个 Signal）
        """
        symbol = self._extract_symbol(data) or self._symbol

        report = self._get_cached_or_fetch(symbol)
        if report is None:
            logger.warning(f"[{self._strategy_id}] 无法获取 {symbol} 的投研报告，产生 HOLD")
            return [
                Signal(
                    symbol=symbol,
                    action="HOLD",
                    strength=0.0,
                    reason="投研报告获取失败，降级为 HOLD",
                    params={"fallback": True, "symbol": symbol},
                )
            ]

        verdict, confidence, score, report_time = self._extract_verdict_from_report(
            report, symbol
        )

        if verdict is None:
            logger.warning(f"[{self._strategy_id}] 报告中无 {symbol} 的评级数据")
            return [
                Signal(
                    symbol=symbol,
                    action="HOLD",
                    strength=0.0,
                    reason="报告中无该股票评级",
                    params={"fallback": True},
                )
            ]

        decay_factor = self._calculate_decay_factor(report_time or "")
        signal = self._verdict_to_signal(verdict, confidence or 0.5, score or 50, decay_factor)

        return [signal]

    def _extract_symbol(self, data: pd.DataFrame) -> str:
        """从数据中提取股票代码"""
        if "symbol" in data.columns and len(data) > 0:
            return str(data["symbol"].iloc[0])
        return ""

    def get_info(self) -> Dict[str, Any]:
        """获取策略信息"""
        info = super().get_info()
        info["symbol"] = self._symbol
        info["refresh_interval"] = self._refresh_interval
        info["expiry_hours"] = self._expiry_hours
        info["has_provider"] = self._report_provider is not None
        info["has_cached_report"] = self._cached_report is not None
        return info

    def validate(self) -> bool:
        """验证策略配置"""
        if not self._symbol:
            logger.error(f"[{self._strategy_id}] 验证失败: 未设置 symbol")
            return False
        if self._refresh_interval < 1:
            logger.error(f"[{self._strategy_id}] 验证失败: refresh_interval 应 >= 1")
            return False
        if self._expiry_hours <= 0:
            logger.error(f"[{self._strategy_id}] 验证失败: expiry_hours 应 > 0")
            return False
        return True
