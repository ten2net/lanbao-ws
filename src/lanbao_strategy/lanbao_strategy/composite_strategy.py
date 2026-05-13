"""
组合策略（信号叠加器）

聚合多个子策略的信号，通过加权投票产生最终交易决策。
支持加权求和、多数决、一致通过三种投票模式。
"""
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
import pandas as pd
from loguru import logger

from .strategy_template import StrategyTemplate, Signal, StrategyParams


@dataclass
class SubStrategyConfig:
    """子策略配置"""
    strategy: StrategyTemplate
    weight: float = 1.0
    strategy_id: str = ""


class CompositeStrategy(StrategyTemplate):
    """
    组合策略（信号叠加器）

    聚合多个子策略的信号，通过加权投票产生最终交易决策。

    支持的投票模式：
    - weighted_sum: 加权和模式（默认）
    - majority: 多数决模式
    - unanimous: 一致通过模式

    子策略可以是技术指标策略、AI投研策略，甚至嵌套的 CompositeStrategy。
    权重可以为负值，表示反向信号。
    """

    VOTING_WEIGHTED_SUM = "weighted_sum"
    VOTING_MAJORITY = "majority"
    VOTING_UNANIMOUS = "unanimous"

    def __init__(
        self,
        strategy_id: str,
        name: str = "组合策略",
        sub_strategies: Optional[List[Dict[str, Any]]] = None,
        weights: Optional[Dict[str, float]] = None,
        voting_mode: str = "weighted_sum",
        threshold_buy: float = 0.2,
        threshold_sell: float = -0.2,
        min_confidence: float = 0.5,
        params: Optional[StrategyParams] = None,
    ):
        """
        初始化组合策略

        Args:
            strategy_id: 策略ID
            name: 策略名称
            sub_strategies: 子策略实例列表，每个元素为 SubStrategyConfig 或 dict
            weights: 权重字典 {strategy_id: weight}
            voting_mode: 投票模式
            threshold_buy: 买入阈值（weighted_sum 模式使用）
            threshold_sell: 卖出阈值（weighted_sum 模式使用）
            min_confidence: 最低置信度（majority 模式使用）
            params: 策略参数
        """
        super().__init__(strategy_id, name, params)

        self._sub_strategies: List[SubStrategyConfig] = []
        self._weights: Dict[str, float] = weights or {}
        self._voting_mode = voting_mode
        self._threshold_buy = threshold_buy
        self._threshold_sell = threshold_sell
        self._min_confidence = min_confidence

        # 初始化子策略
        if sub_strategies:
            self._init_sub_strategies(sub_strategies)

    def _init_sub_strategies(self, configs: List[Dict[str, Any]]):
        """初始化子策略"""
        for cfg in configs:
            if isinstance(cfg, SubStrategyConfig):
                self._sub_strategies.append(cfg)
            elif isinstance(cfg, dict):
                strategy = cfg.get("strategy")
                if strategy is None:
                    logger.warning(f"[{self._strategy_id}] 子策略配置缺少 strategy 实例，跳过")
                    continue
                weight = cfg.get("weight", 1.0)
                sid = getattr(strategy, "strategy_id", "")
                self._sub_strategies.append(
                    SubStrategyConfig(strategy=strategy, weight=weight, strategy_id=sid)
                )
                # 同步到权重字典
                if sid:
                    self._weights[sid] = weight
            elif isinstance(cfg, StrategyTemplate):
                sid = cfg.strategy_id
                weight = self._weights.get(sid, 1.0)
                self._sub_strategies.append(
                    SubStrategyConfig(strategy=cfg, weight=weight, strategy_id=sid)
                )

    @property
    def sub_strategies(self) -> List[SubStrategyConfig]:
        """获取子策略列表"""
        return self._sub_strategies.copy()

    @property
    def voting_mode(self) -> str:
        """获取投票模式"""
        return self._voting_mode

    def add_sub_strategy(self, strategy: StrategyTemplate, weight: float = 1.0):
        """
        添加子策略

        Args:
            strategy: 子策略实例
            weight: 权重（可为负值表示反向）
        """
        sid = strategy.strategy_id
        self._sub_strategies.append(
            SubStrategyConfig(strategy=strategy, weight=weight, strategy_id=sid)
        )
        self._weights[sid] = weight
        logger.info(f"[{self._strategy_id}] 添加子策略: {sid}, 权重: {weight}")

    def remove_sub_strategy(self, strategy_id: str) -> bool:
        """
        移除子策略

        Args:
            strategy_id: 子策略ID

        Returns:
            是否成功移除
        """
        original_len = len(self._sub_strategies)
        self._sub_strategies = [
            s for s in self._sub_strategies if s.strategy_id != strategy_id
        ]
        if strategy_id in self._weights:
            del self._weights[strategy_id]

        removed = len(self._sub_strategies) < original_len
        if removed:
            logger.info(f"[{self._strategy_id}] 移除子策略: {strategy_id}")
        return removed

    def set_weight(self, strategy_id: str, weight: float):
        """
        设置子策略权重

        Args:
            strategy_id: 子策略ID
            weight: 新权重
        """
        self._weights[strategy_id] = weight
        for sub in self._sub_strategies:
            if sub.strategy_id == strategy_id:
                sub.weight = weight
                break
        logger.info(f"[{self._strategy_id}] 设置权重: {strategy_id} = {weight}")

    def analyze(self, data: pd.DataFrame) -> Dict[str, Any]:
        """
        聚合分析所有子策略

        Args:
            data: 市场数据

        Returns:
            聚合分析结果
        """
        if not self._sub_strategies:
            return {"error": "无子策略", "sub_analyses": {}}

        sub_analyses = {}
        for sub in self._sub_strategies:
            try:
                analysis = sub.strategy.analyze(data)
                sub_analyses[sub.strategy_id] = {
                    "analysis": analysis,
                    "weight": sub.weight,
                }
            except Exception as e:
                logger.error(f"[{self._strategy_id}] 子策略 {sub.strategy_id} 分析失败: {e}")
                sub_analyses[sub.strategy_id] = {"error": str(e), "weight": sub.weight}

        return {
            "voting_mode": self._voting_mode,
            "sub_strategy_count": len(self._sub_strategies),
            "sub_analyses": sub_analyses,
        }

    def generate_signals(self, data: pd.DataFrame) -> List[Signal]:
        """
        生成聚合交易信号

        Args:
            data: 市场数据

        Returns:
            聚合后的信号列表（通常0或1个信号）
        """
        if not self._sub_strategies:
            logger.warning(f"[{self._strategy_id}] 无子策略，无法生成信号")
            return []

        symbol = self._extract_symbol(data)

        # 收集所有子策略的信号
        all_signals: List[Signal] = []
        for sub in self._sub_strategies:
            try:
                signals = sub.strategy.generate_signals(data)
                for sig in signals:
                    # 为信号标注来源，便于调试
                    sig.params["source_strategy"] = sub.strategy_id
                    sig.params["source_weight"] = sub.weight
                all_signals.extend(signals)
            except Exception as e:
                logger.error(
                    f"[{self._strategy_id}] 子策略 {sub.strategy_id} 生成信号失败: {e}"
                )

        if not all_signals:
            return []

        # 根据投票模式聚合
        aggregated = self._aggregate_signals(all_signals, symbol)
        if aggregated:
            aggregated.params["composite_mode"] = self._voting_mode
            aggregated.params["sub_signal_count"] = len(all_signals)
            return [aggregated]
        return []

    def _aggregate_signals(
        self, signals: List[Signal], symbol: str
    ) -> Optional[Signal]:
        """
        根据投票模式聚合信号

        Args:
            signals: 子策略信号列表
            symbol: 股票代码

        Returns:
            聚合后的信号，或无信号时返回 None
        """
        if self._voting_mode == self.VOTING_WEIGHTED_SUM:
            return self._aggregate_weighted_sum(signals, symbol)
        elif self._voting_mode == self.VOTING_MAJORITY:
            return self._aggregate_majority(signals, symbol)
        elif self._voting_mode == self.VOTING_UNANIMOUS:
            return self._aggregate_unanimous(signals, symbol)
        else:
            logger.error(f"[{self._strategy_id}] 未知投票模式: {self._voting_mode}")
            return None

    def _aggregate_weighted_sum(
        self, signals: List[Signal], symbol: str
    ) -> Optional[Signal]:
        """
        加权和模式

        将各信号映射为数值，加权求和后根据阈值判断。
        BUY=+1, SELL=-1, HOLD=0
        """
        score_map = {"BUY": 1.0, "SELL": -1.0, "HOLD": 0.0}

        weighted_sum = 0.0
        total_weight = 0.0
        active_count = 0

        for sig in signals:
            direction = score_map.get(sig.action, 0.0)
            if direction == 0.0:
                continue  # 跳过 HOLD 信号

            source_id = sig.params.get("source_strategy", "")
            weight = self._weights.get(source_id, 1.0)

            weighted_sum += direction * weight * sig.strength
            total_weight += abs(weight)
            active_count += 1

        if total_weight == 0 or active_count == 0:
            return None

        final_score = weighted_sum / total_weight

        # 根据阈值判断
        if final_score >= self._threshold_buy:
            action = "BUY"
            strength = min(abs(final_score), 1.0)
            reason = (
                f"加权得分 {final_score:.2f} >= 买入阈值 {self._threshold_buy} "
                f"(基于 {active_count} 个活跃信号)"
            )
        elif final_score <= self._threshold_sell:
            action = "SELL"
            strength = min(abs(final_score), 1.0)
            reason = (
                f"加权得分 {final_score:.2f} <= 卖出阈值 {self._threshold_sell} "
                f"(基于 {active_count} 个活跃信号)"
            )
        else:
            return None  # 无信号

        return Signal(
            symbol=symbol,
            action=action,
            strength=strength,
            reason=reason,
            params={
                "final_score": round(final_score, 4),
                "threshold_buy": self._threshold_buy,
                "threshold_sell": self._threshold_sell,
            },
        )

    def _aggregate_majority(
        self, signals: List[Signal], symbol: str
    ) -> Optional[Signal]:
        """
        多数决模式

        BUY 票数 vs SELL 票数，需超过 min_confidence 比例。
        """
        total_weight = 0.0
        buy_weight = 0.0
        sell_weight = 0.0
        active_count = 0

        for sig in signals:
            if sig.action == "HOLD":
                continue

            source_id = sig.params.get("source_strategy", "")
            weight = self._weights.get(source_id, 1.0)
            abs_weight = abs(weight)
            total_weight += abs_weight
            active_count += 1

            # 负权重反转信号方向
            effective_direction = sig.action if weight >= 0 else self._reverse_action(sig.action)

            if effective_direction == "BUY":
                buy_weight += abs_weight * sig.strength
            elif effective_direction == "SELL":
                sell_weight += abs_weight * sig.strength

        if total_weight == 0 or active_count == 0:
            return None

        # 检查是否超过最低置信度
        required_votes = total_weight * self._min_confidence

        if buy_weight > sell_weight and buy_weight >= required_votes:
            action = "BUY"
            strength = min(buy_weight / total_weight, 1.0)
            reason = (
                f"多数决: BUY 票数 {buy_weight:.2f} > SELL 票数 {sell_weight:.2f}, "
                f"满足最低置信度 {self._min_confidence}"
            )
        elif sell_weight > buy_weight and sell_weight >= required_votes:
            action = "SELL"
            strength = min(sell_weight / total_weight, 1.0)
            reason = (
                f"多数决: SELL 票数 {sell_weight:.2f} > BUY 票数 {buy_weight:.2f}, "
                f"满足最低置信度 {self._min_confidence}"
            )
        else:
            return None

        return Signal(
            symbol=symbol,
            action=action,
            strength=strength,
            reason=reason,
            params={
                "buy_votes": round(buy_weight, 4),
                "sell_votes": round(sell_weight, 4),
                "required_votes": round(required_votes, 4),
            },
        )

    def _aggregate_unanimous(
        self, signals: List[Signal], symbol: str
    ) -> Optional[Signal]:
        """
        一致通过模式

        所有活跃信号方向必须一致，且达到 min_confidence。
        """
        actions = set()
        total_weight = 0.0
        total_strength = 0.0
        active_count = 0

        for sig in signals:
            if sig.action == "HOLD":
                continue

            source_id = sig.params.get("source_strategy", "")
            weight = self._weights.get(source_id, 1.0)
            abs_weight = abs(weight)

            effective_action = sig.action if weight >= 0 else self._reverse_action(sig.action)
            actions.add(effective_action)
            total_weight += abs_weight
            total_strength += abs_weight * sig.strength
            active_count += 1

        if len(actions) != 1 or active_count == 0:
            return None

        # 检查是否达到最低置信度（权重比例）
        confidence = total_strength / total_weight if total_weight > 0 else 0
        if confidence < self._min_confidence:
            return None

        action = actions.pop()
        strength = min(confidence, 1.0)
        reason = (
            f"一致通过: 所有 {active_count} 个活跃信号均为 {action}, "
            f"置信度 {confidence:.2f} >= {self._min_confidence}"
        )

        return Signal(
            symbol=symbol,
            action=action,
            strength=strength,
            reason=reason,
            params={
                "unanimous_count": active_count,
                "confidence": round(confidence, 4),
            },
        )

    @staticmethod
    def _reverse_action(action: str) -> str:
        """反转信号方向（用于负权重）"""
        mapping = {"BUY": "SELL", "SELL": "BUY", "HOLD": "HOLD"}
        return mapping.get(action, action)

    def _extract_symbol(self, data: pd.DataFrame) -> str:
        """从数据中提取股票代码"""
        if "symbol" in data.columns:
            return str(data["symbol"].iloc[0])
        return "UNKNOWN"

    def get_info(self) -> Dict[str, Any]:
        """获取策略信息（包含子策略）"""
        info = super().get_info()
        info["voting_mode"] = self._voting_mode
        info["threshold_buy"] = self._threshold_buy
        info["threshold_sell"] = self._threshold_sell
        info["min_confidence"] = self._min_confidence
        info["sub_strategies"] = [
            {
                "strategy_id": sub.strategy_id,
                "name": sub.strategy.name,
                "weight": sub.weight,
                "state": sub.strategy.state,
            }
            for sub in self._sub_strategies
        ]
        return info

    def validate(self) -> bool:
        """验证组合策略配置"""
        if not self._sub_strategies:
            logger.error(f"[{self._strategy_id}] 验证失败: 无子策略")
            return False
        if len(self._sub_strategies) > 10:
            logger.error(f"[{self._strategy_id}] 验证失败: 子策略数量超过 10")
            return False
        if self._threshold_buy <= self._threshold_sell:
            logger.error(f"[{self._strategy_id}] 验证失败: 买入阈值应大于卖出阈值")
            return False
        if not 0 <= self._min_confidence <= 1:
            logger.error(f"[{self._strategy_id}] 验证失败: min_confidence 应在 [0, 1]")
            return False
        return True

    def to_signal_generator(self) -> Callable[[pd.DataFrame], pd.Series]:
        """
        转换为回测兼容的信号生成器

        返回函数接受 DataFrame，输出 pd.Series（-1/0/1）
        """
        score_map = {"BUY": 1, "SELL": -1, "HOLD": 0}

        def generator(data: pd.DataFrame) -> pd.Series:
            signals = self.generate_signals(data)
            if signals:
                return pd.Series([score_map.get(signals[0].action, 0)], index=[data.index[-1]])
            return pd.Series([0], index=[data.index[-1]])

        return generator
