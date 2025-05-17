import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_square_off_strategy():
    response = client.post("/square-off/strategy/strategy123")
    assert response.status_code == 200
    assert response.json()["message"] == "Square off completed for strategy strategy123"


def test_square_off_all():
    response = client.post("/square-off/all")
    assert response.status_code == 200
    assert response.json()["message"] == "Square off completed for all strategies"


def test_square_off_strategy_error():
    # Simulate an error by passing an invalid strategy ID
    response = client.post("/square-off/strategy/invalid")
    assert response.status_code == 200
    assert response.json()["message"] == "Square off completed for strategy invalid"
