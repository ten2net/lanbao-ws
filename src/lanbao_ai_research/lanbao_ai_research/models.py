"""投研分析数据模型"""
from typing import List, Dict, Any, Optional
from enum import Enum
from datetime import datetime
from pydantic import BaseModel, Field


class Verdict(str, Enum):
    """投资评级"""
    STRONG_BUY = "STRONG_BUY"
    BUY = "BUY"
    HOLD = "HOLD"
    SELL = "SELL"
    STRONG_SELL = "STRONG_SELL"


class MarketTrend(str, Enum):
    """市场趋势"""
    UP = "UP"
    DOWN = "DOWN"
    SIDEWAYS = "SIDEWAYS"


class MacroReport(BaseModel):
    """宏观分析报告"""
    agent: str = "macro_analyst"
    market_trend: MarketTrend = MarketTrend.SIDEWAYS
    trend_strength: float = Field(0.0, ge=0.0, le=1.0)
    sector_hot: List[str] = Field(default_factory=list)
    sector_cold: List[str] = Field(default_factory=list)
    policy_impact: str = ""
    key_events: List[str] = Field(default_factory=list)
    risk_level: str = "中"
    raw_analysis: str = ""


class FundamentalReport(BaseModel):
    """基本面分析报告"""
    verdict: Verdict = Verdict.HOLD
    score: int = Field(50, ge=0, le=100)
    pe_ttm: Optional[float] = None
    pb: Optional[float] = None
    roe: Optional[float] = None
    debt_ratio: Optional[float] = None
    revenue_growth: Optional[float] = None
    profit_growth: Optional[float] = None
    key_points: List[str] = Field(default_factory=list)
    concerns: List[str] = Field(default_factory=list)
    raw_analysis: str = ""


class TechnicalReport(BaseModel):
    """技术面分析报告"""
    verdict: Verdict = Verdict.HOLD
    score: int = Field(50, ge=0, le=100)
    trend: str = "震荡"
    support: Optional[float] = None
    resistance: Optional[float] = None
    patterns: List[str] = Field(default_factory=list)
    signals: List[str] = Field(default_factory=list)
    raw_analysis: str = ""


class SentimentReport(BaseModel):
    """情绪与新闻分析报告"""
    verdict: Verdict = Verdict.HOLD
    score: int = Field(50, ge=0, le=100)
    sentiment_score: float = Field(0.0, ge=-1.0, le=1.0)
    news_summary: str = ""
    capital_trend: str = ""
    hot_degree: str = ""
    raw_analysis: str = ""


class StockSynthesis(BaseModel):
    """个股综合评估"""
    verdict: Verdict = Verdict.HOLD
    score: int = Field(50, ge=0, le=100)
    bull_case: List[str] = Field(default_factory=list)
    bear_case: List[str] = Field(default_factory=list)
    position_suggestion: str = ""
    risk_notes: List[str] = Field(default_factory=list)


class StockAnalysis(BaseModel):
    """个股完整分析"""
    symbol: str
    name: str = ""
    fundamental: Optional[FundamentalReport] = None
    technical: Optional[TechnicalReport] = None
    sentiment: Optional[SentimentReport] = None
    synthesis: Optional[StockSynthesis] = None


class PortfolioSuggestions(BaseModel):
    """投资组合建议"""
    top_picks: List[str] = Field(default_factory=list)
    avoid_list: List[str] = Field(default_factory=list)
    sector_allocation: Dict[str, float] = Field(default_factory=dict)


class ReportSummary(BaseModel):
    """报告摘要"""
    market_trend: str = ""
    overall_verdict: Verdict = Verdict.HOLD
    confidence: float = Field(0.5, ge=0.0, le=1.0)
    top_sectors: List[str] = Field(default_factory=list)
    risk_level: str = "中"


class ResearchReport(BaseModel):
    """投研报告完整模型"""
    report_id: str
    report_type: str = "market_daily"
    created_at: str = ""
    summary: ReportSummary = Field(default_factory=ReportSummary)
    macro_analysis: Optional[MacroReport] = None
    stock_analyses: List[StockAnalysis] = Field(default_factory=list)
    portfolio_suggestions: PortfolioSuggestions = Field(default_factory=PortfolioSuggestions)

    def to_json(self) -> str:
        return self.model_dump_json(indent=2, ensure_ascii=False)

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()


class AnalysisContext(BaseModel):
    """分析上下文"""
    symbol: Optional[str] = None
    market_data: Optional[Dict[str, Any]] = None
    financial_data: Optional[Dict[str, Any]] = None
    news_items: List[str] = Field(default_factory=list)
    macro_context: Optional[str] = None


class AgentReport(BaseModel):
    """单个智能体报告"""
    agent_name: str
    success: bool = True
    error_message: Optional[str] = None
    data: Dict[str, Any] = Field(default_factory=dict)
    raw_text: str = ""
    duration_seconds: float = 0.0
