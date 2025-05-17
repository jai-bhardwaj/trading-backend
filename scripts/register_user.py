import requests
import json


def register_user(username: str, email: str, password: str):
    """
    Register a new user with the trading application.

    Args:
        username (str): The username for the new user (will be used as id)
        email (str): The email address for the new user
        password (str): The password for the new user

    Returns:
        dict: The response from the server containing the access token
    """
    # API endpoint
    url = "http://localhost:8000/auth/register"

    # Request payload
    payload = {"id": username, "email": email, "password": password}

    # Headers
    headers = {"Content-Type": "application/json"}

    try:
        # Make the POST request
        response = requests.post(url, json=payload, headers=headers)

        # Check if the request was successful
        response.raise_for_status()

        # Return the response data
        return response.json()

    except requests.exceptions.RequestException as e:
        print(f"Error registering user: {str(e)}")
        if hasattr(e.response, "text"):
            print(f"Server response: {e.response.text}")
        return None


if __name__ == "__main__":
    # Example usage
    username = input("Enter username: ")
    email = input("Enter email: ")
    password = input("Enter password: ")

    result = register_user(username, email, password)

    if result:
        print("\nRegistration successful!")
        print("Access token:", result.get("access_token"))
    else:
        print("\nRegistration failed. Please check the error message above.")
