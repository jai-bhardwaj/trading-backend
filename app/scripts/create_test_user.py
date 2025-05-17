import requests
import json

# API endpoints
BASE_URL = "http://localhost:8000"
REGISTER_URL = f"{BASE_URL}/auth/register"


def register_test_user():
    """Register a test user"""
    user_data = {
        "username": "testuser",
        "email": "test@example.com",
        "password": "testpass",
    }

    response = requests.post(REGISTER_URL, json=user_data)
    if response.status_code != 200:
        raise Exception(f"Registration failed: {response.text}")
    return response.json()


if __name__ == "__main__":
    try:
        print("Registering test user...")
        result = register_test_user()
        print("User registered successfully!")
        print("\nUser details:")
        print(json.dumps(result, indent=2))
    except Exception as e:
        print(f"Error: {str(e)}")
