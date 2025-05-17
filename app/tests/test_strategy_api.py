import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


@pytest.fixture(scope="module")
def user_token():
    # Register a new user
    username = "apitestuser"
    email = "apitestuser@example.com"
    password = "testpassword"
    client.post(
        "/auth/register",
        json={"username": username, "email": email, "password": password},
    )
    # Login to get token
    resp = client.post("/auth/token", data={"username": username, "password": password})
    assert resp.status_code == 200
    token = resp.json()["access_token"]
    return token


def auth_headers(token):
    return {"Authorization": f"Bearer {token}"}


def test_create_strategy(user_token):
    data = {
        "name": "Test Strategy",
        "symbol": "AAPL",
        "entry_price": 100.0,
        "quantity": 10,
    }
    resp = client.post("/strategies", json=data, headers=auth_headers(user_token))
    assert resp.status_code == 201
    result = resp.json()
    assert result["name"] == data["name"]
    assert result["symbol"] == data["symbol"]
    assert result["entry_price"] == data["entry_price"]
    assert result["quantity"] == data["quantity"]
    global strategy_id
    strategy_id = result["id"]


def test_get_strategies(user_token):
    resp = client.get("/strategies", headers=auth_headers(user_token))
    assert resp.status_code == 200
    strategies = resp.json()
    assert isinstance(strategies, list)
    assert any(s["name"] == "Test Strategy" for s in strategies)


def test_update_strategy(user_token):
    update = {
        "name": "Updated Strategy",
        "symbol": "AAPL",
        "entry_price": 120.0,
        "quantity": 5,
    }
    resp = client.put(
        f"/strategies/{strategy_id}", json=update, headers=auth_headers(user_token)
    )
    assert resp.status_code == 200
    result = resp.json()
    assert result["name"] == update["name"]
    assert result["entry_price"] == update["entry_price"]


def test_mock_active_strategy(user_token):
    resp = client.post(
        f"/strategies/{strategy_id}/mock_active", headers=auth_headers(user_token)
    )
    assert resp.status_code == 200
    assert resp.json()["message"] == "Strategy set to active"


def test_delete_strategy(user_token):
    resp = client.delete(f"/strategies/{strategy_id}", headers=auth_headers(user_token))
    assert resp.status_code == 204
    # Confirm it's gone
    resp2 = client.get("/strategies", headers=auth_headers(user_token))
    assert all(s["id"] != strategy_id for s in resp2.json())


def test_unauthorized_access():
    # Should fail without token
    resp = client.get("/strategies")
    assert resp.status_code == 401
    resp = client.post(
        "/strategies",
        json={"name": "x", "symbol": "x", "entry_price": 1, "quantity": 1},
    )
    assert resp.status_code == 401
