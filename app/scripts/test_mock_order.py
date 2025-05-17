import requests
import json
import os
from datetime import datetime

# API endpoints
BASE_URL = "http://localhost:8000"
LOGIN_URL = f"{BASE_URL}/auth/token"
ORDERS_URL = f"{BASE_URL}/orders"


def login(username: str, password: str) -> str:
    """Login and get access token"""
    response = requests.post(
        LOGIN_URL, data={"username": username, "password": password}
    )
    if response.status_code != 200:
        raise Exception(f"Login failed: {response.text}")
    return response.json()["access_token"]


def create_mock_order(token: str) -> dict:
    """Create a mock order using the provided token"""
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    order_data = {
        "symbol": "SBIN-EQ",
        "exchange": "NSE",
        "product_type": "INTRADAY",
        "order_type": "LIMIT",
        "side": "BUY",
        "quantity": 10,
        "price": 350.50,
        "trigger_price": 348.00,
        "variety": "NORMAL",
        "tag": f"test_order_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "broker_id": "mock_broker",
        "is_paper_trade": True,
    }

    response = requests.post(ORDERS_URL, headers=headers, json=order_data)
    if response.status_code != 202:
        raise Exception(f"Order creation failed: {response.text}")
    return response.json()


def main():
    # Get credentials from environment variables or use defaults for testing
    username = os.getenv("TEST_USERNAME", "testuser")
    password = os.getenv("TEST_PASSWORD", "testpass")

    try:
        print("Logging in...")
        token = login(username, password)
        print("Login successful!")

        print("\nCreating mock order...")
        order_response = create_mock_order(token)
        print("Order created successfully!")
        print("\nOrder details:")
        print(json.dumps(order_response, indent=2))

    except Exception as e:
        print(f"Error: {str(e)}")


if __name__ == "__main__":
    main()
