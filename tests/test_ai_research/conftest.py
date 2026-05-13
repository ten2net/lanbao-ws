"""测试 fixtures"""
import pytest

from lanbao_ai_research.llm.client import LLMClient
from lanbao_ai_research.llm.providers.base import LLMConfig


class MockLLMClient(LLMClient):
    """Mock LLM 客户端，返回固定响应"""

    def __init__(self, responses=None):
        self.responses = responses or {}
        self.calls = []

    async def complete(self, prompt, system=None, temperature=None):
        self.calls.append({"prompt": prompt, "system": system})
        # 优先检查更具体的 prompt，避免 JSON 数据中的关键词误匹配
        if "投资总监" in prompt or "portfolio director" in prompt.lower():
            return '{"summary": {"market_trend": "上涨", "overall_verdict": "BUY", "confidence": 0.8, "top_sectors": ["科技"], "risk_level": "中"}, "stock_analyses": [{"symbol": "600519", "synthesis": {"verdict": "BUY", "score": 75, "bull_case": ["理由1"], "bear_case": ["风险1"], "position_suggestion": "10%", "risk_notes": ["注意回调"]}}], "portfolio_suggestions": {"top_picks": ["600519"], "avoid_list": [], "sector_allocation": {"科技": 0.3}}}'
        elif "宏观分析师" in prompt or "macro analyst" in prompt.lower():
            return '{"market_trend": "UP", "trend_strength": 0.7, "sector_hot": ["科技"], "policy_impact": "利好", "risk_level": "中", "raw_analysis": "测试"}'
        elif "基本面分析师" in prompt or "fundamental analyst" in prompt.lower():
            return '{"verdict": "BUY", "score": 80, "pe_ttm": 20, "pb": 3, "roe": 15, "key_points": ["财务稳健"], "concerns": ["估值偏高"], "raw_analysis": "测试"}'
        elif "技术分析师" in prompt or "technical analyst" in prompt.lower():
            return '{"verdict": "BUY", "score": 75, "trend": "上涨", "support": 10, "resistance": 20, "patterns": ["头肩底"], "signals": ["金叉"], "raw_analysis": "测试"}'
        elif "情绪分析师" in prompt or "sentiment analyst" in prompt.lower():
            return '{"verdict": "BUY", "score": 70, "sentiment_score": 0.5, "news_summary": "积极", "capital_trend": "流入", "hot_degree": "高", "raw_analysis": "测试"}'
        return '{"raw_analysis": "默认响应"}'


@pytest.fixture
def mock_llm():
    return MockLLMClient()
