"""API 测试配置"""
import pytest
from fastapi.testclient import TestClient

from lanbao_backtest.api.main import app


@pytest.fixture
def client():
    """FastAPI TestClient"""
    return TestClient(app)
