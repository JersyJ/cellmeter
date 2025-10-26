import requests

from app.config import get_settings

API_TOKEN = None


def get_teltonika_token():
    """Authenticates with Teltonika and gets a session token."""
    global API_TOKEN
    try:
        response = requests.post(
            f"http://{get_settings().teltonika.ip}/api/login",
            json={
                "username": get_settings().teltonika.user,
                "password": get_settings().teltonika.password.get_secret_value(),
            },
            timeout=5,
        )
        response.raise_for_status()
        API_TOKEN = response.json().get("token")
        print("Successfully authenticated with Teltonika.")
        return API_TOKEN
    except requests.RequestException as e:
        print(f"Error authenticating with Teltonika: {e}")
        API_TOKEN = None
        return None


def get_modem_status():
    """Polls the modem status endpoint for cellular and GPS data."""
    if not API_TOKEN:
        print("No auth token, attempting to re-authenticate.")
        get_teltonika_token()
        if not API_TOKEN:
            return None

    try:
        response = requests.get(
            f"http://{get_settings().teltonika.ip}/api/v1/modem/status",
            headers={"Authorization": f"Bearer {API_TOKEN}"},
            timeout=5,
        )
        if response.status_code == 401:  # Token expired
            print("Token expired, re-authenticating.")
            get_teltonika_token()
            return get_modem_status()  # Retry once

        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"Error getting modem status: {e}")
        return None
