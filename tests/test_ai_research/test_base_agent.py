"""BaseAgent 测试"""
import pytest
from lanbao_ai_research.agents.base_agent import BaseAgent
from lanbao_ai_research.models import AnalysisContext, AgentReport


class DummyAgent(BaseAgent):
    """测试用的 Dummy Agent"""

    async def analyze(self, context: AnalysisContext) -> AgentReport:
        return AgentReport(agent_name="dummy", success=True)


class TestParseJsonResponse:
    """测试 JSON 解析"""

    def test_direct_json(self, mock_llm):
        agent = DummyAgent("test", mock_llm)
        result = agent._parse_json_response('{"key": "value"}')
        assert result == {"key": "value"}

    def test_markdown_code_block(self, mock_llm):
        agent = DummyAgent("test", mock_llm)
        text = '```json\n{"key": "value"}\n```'
        result = agent._parse_json_response(text)
        assert result == {"key": "value"}

    def test_invalid_json_returns_none(self, mock_llm):
        agent = DummyAgent("test", mock_llm)
        result = agent._parse_json_response('not json')
        assert result is None

    def test_nested_braces(self, mock_llm):
        agent = DummyAgent("test", mock_llm)
        text = 'some text {"key": "value"} more text'
        result = agent._parse_json_response(text)
        assert result == {"key": "value"}
