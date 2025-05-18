import requests
import json
from urllib.parse import urlencode


def register_user(username: str, email: str, password: str):
    """Register a new user"""
    url = "http://localhost:8000/auth/register"
    payload = {"username": username, "email": email, "password": password}
    headers = {"Content-Type": "application/json"}

    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Registration error: {str(e)}")
        if hasattr(e, "response") and e.response is not None:
            print(f"Server response: {e.response.text}")
        return None


def login_user(username: str, password: str):
    """Login with username and password"""
    url = "http://localhost:8000/auth/token"
    # Note: Using form data for login as per OAuth2PasswordRequestForm
    data = {"username": username, "password": password}
    headers = {"Content-Type": "application/x-www-form-urlencoded"}

    try:
        response = requests.post(url, data=urlencode(data), headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Login error: {str(e)}")
        if hasattr(e, "response") and e.response is not None:
            print(f"Server response: {e.response.text}")
        return None


if __name__ == "__main__":
    # Test login with new test user
    print("Testing login with test user...")
    username = "testuser4"
    password = "testpassword123"

    login_result = login_user(username, password)
    if login_result:
        print("Login successful!")
        print("Access token:", login_result.get("access_token"))
    else:
        print("Login failed!")
