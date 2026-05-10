"""策略管理路由"""
from fastapi import APIRouter, HTTPException

from ..models import StrategyListResponse, StrategyTemplate

router = APIRouter()

# 内置策略模板（与 StrategyFactory 保持一致）
STRATEGIES = [
    StrategyTemplate(
        strategy_id="ma_cross",
        name="双均线交叉策略",
        description="金叉买入，死叉卖出",
        default_params={
            "fast_period": 5,
            "slow_period": 20,
            "initial_capital": 100000,
            "commission_rate": 0.0003,
            "slippage": 0.001,
        },
    ),
    StrategyTemplate(
        strategy_id="rsi",
        name="RSI策略",
        description="超卖买入，超买卖出",
        default_params={
            "period": 14,
            "oversold": 30,
            "overbought": 70,
            "initial_capital": 100000,
            "commission_rate": 0.0003,
            "slippage": 0.001,
        },
    ),
    StrategyTemplate(
        strategy_id="macd",
        name="MACD策略",
        description="MACD金叉买入，死叉卖出",
        default_params={
            "fast": 12,
            "slow": 26,
            "signal": 9,
            "initial_capital": 100000,
            "commission_rate": 0.0003,
            "slippage": 0.001,
        },
    ),
]


@router.get("/strategies", response_model=StrategyListResponse)
async def list_strategies():
    """获取策略模板列表"""
    return StrategyListResponse(strategies=STRATEGIES)


@router.get("/strategies/{strategy_id}")
async def get_strategy(strategy_id: str):
    """获取策略模板详情"""
    for s in STRATEGIES:
        if s.strategy_id == strategy_id:
            return s
    raise HTTPException(status_code=404, detail=f"策略模板不存在: {strategy_id}")
