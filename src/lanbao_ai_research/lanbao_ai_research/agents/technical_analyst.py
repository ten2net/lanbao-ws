"""技术分析师智能体"""
import json
import time

import pandas as pd
import numpy as np
from loguru import logger

from .base_agent import BaseAgent
from ..models import AgentReport, AnalysisContext, TechnicalReport


class TechnicalAnalyst(BaseAgent):
    """技术分析师 — 分析 K 线形态、技术指标"""

    def __init__(self, llm_client):
        super().__init__("technical_analyst", llm_client, "technical_analyst.txt")

    def _calculate_indicators(self, df: pd.DataFrame) -> dict:
        """计算技术指标"""
        if df is None or len(df) < 20:
            return {}

        close = df['close']

        ma5 = close.rolling(5).mean().iloc[-1]
        ma10 = close.rolling(10).mean().iloc[-1]
        ma20 = close.rolling(20).mean().iloc[-1]
        ma60 = close.rolling(60).mean().iloc[-1] if len(close) >= 60 else None

        delta = close.diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))

        exp1 = close.ewm(span=12, adjust=False).mean()
        exp2 = close.ewm(span=26, adjust=False).mean()
        macd = exp1 - exp2
        signal = macd.ewm(span=9, adjust=False).mean()
        hist = macd - signal

        ma20_line = close.rolling(20).mean()
        std20 = close.rolling(20).std()
        upper = ma20_line + 2 * std20
        lower = ma20_line - 2 * std20

        result = {
            "current_price": close.iloc[-1],
            "ma5": ma5, "ma10": ma10, "ma20": ma20,
            "rsi": rsi.iloc[-1],
            "macd": macd.iloc[-1],
            "macd_signal": signal.iloc[-1],
            "macd_hist": hist.iloc[-1],
            "boll_upper": upper.iloc[-1],
            "boll_lower": lower.iloc[-1],
        }

        if ma60 is not None:
            result["ma60"] = ma60

        return {k: round(v, 2) if v is not None else None for k, v in result.items()}

    async def analyze(self, context: AnalysisContext) -> AgentReport:
        start = time.time()

        try:
            symbol = context.symbol or "UNKNOWN"
            market_data = context.market_data

            indicators = self._calculate_indicators(market_data)

            recent_data = None
            if market_data is not None and len(market_data) > 0:
                recent = market_data.tail(20)
                recent_data = recent.reset_index().to_dict('records')

            prompt = self._format_prompt(
                symbol=symbol,
                technical_data=json.dumps({
                    "indicators": indicators,
                    "recent_klines": recent_data
                }, ensure_ascii=False, indent=2, default=str)
            )

            response = await self._call_llm(
                prompt,
                system="你是一位资深的技术分析师，只输出 JSON 格式结果。",
                temperature=0.3
            )

            parsed = self._parse_json_response(response)
            report = TechnicalReport(**parsed) if parsed else TechnicalReport()

            return AgentReport(
                agent_name=self.name,
                success=parsed is not None,
                data=report.model_dump(),
                raw_text=response,
                duration_seconds=time.time() - start
            )
        except Exception as e:
            logger.error(f"技术面分析失败 [{context.symbol}]: {e}")
            return AgentReport(
                agent_name=self.name,
                success=False,
                error_message=str(e),
                data=TechnicalReport().model_dump(),
                duration_seconds=time.time() - start
            )
