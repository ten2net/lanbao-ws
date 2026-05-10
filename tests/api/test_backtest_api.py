"""回测 API 集成测试"""
import pytest


def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"


def test_list_strategies(client):
    response = client.get("/api/v1/strategies")
    assert response.status_code == 200
    data = response.json()
    assert len(data["strategies"]) == 3
    strategy_ids = [s["strategy_id"] for s in data["strategies"]]
    assert "ma_cross" in strategy_ids


def test_list_backtests_empty(client):
    response = client.get("/api/v1/backtests")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert data["items"] == []


def test_get_nonexistent_backtest(client):
    response = client.get("/api/v1/backtests/bt_nonexistent")
    assert response.status_code == 404
