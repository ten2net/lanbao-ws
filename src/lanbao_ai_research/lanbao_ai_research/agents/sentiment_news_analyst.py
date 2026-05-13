"""情绪新闻分析师智能体"""
import json
import time
from typing import List

import httpx
from loguru import logger

from .base_agent import BaseAgent
from ..models import AgentReport, AnalysisContext, SentimentReport


class SentimentNewsAnalyst(BaseAgent):
    """情绪新闻分析师 — 分析市场情绪、资金流向、新闻事件"""

    def __init__(self, llm_client, news_enabled: bool = True):
        super().__init__("sentiment_news_analyst", llm_client, "sentiment_news.txt")
        self.news_enabled = news_enabled
        self._news_client = httpx.AsyncClient(timeout=10.0)

    async def _fetch_news(self, symbol: str) -> List[str]:
        if not self.news_enabled:
            return []

        try:
            url = "https://searchapi.eastmoney.com/api/suggest/get"
            params = {"input": symbol, "type": 14, "count": 10}
            response = await self._news_client.get(url, params=params)
            data = response.json()

            news_items = []
            for item in data.get("QuotationCodeTable", {}).get("Data", []):
                if "Title" in item:
                    news_items.append(item["Title"])

            return news_items[:5]
        except Exception as e:
            logger.warning(f"获取新闻失败 [{symbol}]: {e}")
            return []

    async def analyze(self, context: AnalysisContext) -> AgentReport:
        start = time.time()

        try:
            symbol = context.symbol or "UNKNOWN"
            market_data = context.market_data

            news = await self._fetch_news(symbol)

            sentiment = 0.0
            if market_data is not None and len(market_data) > 1:
                recent = market_data.tail(5)
                price_change = (recent['close'].iloc[-1] - recent['close'].iloc[0]) / recent['close'].iloc[0]
                volume_avg = recent['volume'].mean()
                volume_prev = market_data['volume'].tail(10).head(5).mean()
                volume_ratio = volume_avg / volume_prev if volume_prev > 0 else 1.0
                sentiment = price_change * 10 + (volume_ratio - 1) * 0.5
                sentiment = max(-1.0, min(1.0, sentiment))

            prompt = self._format_prompt(
                symbol=symbol,
                market_data=json.dumps({
                    "sentiment_score": round(sentiment, 2),
                    "recent_volume_trend": "放量" if sentiment > 0.2 else "缩量" if sentiment < -0.2 else "平量"
                }, ensure_ascii=False),
                news="\n".join(news) if news else "暂无相关新闻"
            )

            response = await self._call_llm(
                prompt,
                system="你是一位资深的情绪分析师，只输出 JSON 格式结果。",
                temperature=0.4
            )

            parsed = self._parse_json_response(response)
            report = SentimentReport(**parsed) if parsed else SentimentReport()

            return AgentReport(
                agent_name=self.name,
                success=parsed is not None,
                data=report.model_dump(),
                raw_text=response,
                duration_seconds=time.time() - start
            )
        except Exception as e:
            logger.error(f"情绪分析失败 [{context.symbol}]: {e}")
            return AgentReport(
                agent_name=self.name,
                success=False,
                error_message=str(e),
                data=SentimentReport().model_dump(),
                duration_seconds=time.time() - start
            )
