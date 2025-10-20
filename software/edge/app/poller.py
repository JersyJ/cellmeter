import requests
import os

# Load config from environment variables
TELTONIKA_IP = os.getenv("TELTONIKA_IP", "192.168.1.1")
TELTONIKA_USER = os.getenv("TELTONIKA_USER", "admin")
TELTONIKA_PASSWORD = os.getenv("TELTONIKA_PASSWORD") # Load from .env

API_TOKEN = None

def get_teltonika_token():
    """Authenticates with Teltonika and gets a session token."""
    global API_TOKEN
    try:
        response = requests.post(
            f"http://{TELTONIKA_IP}/api/login",
            json={"username": TELTONIKA_USER, "password": TELTONIKA_PASSWORD},
            timeout=5
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
            f"http://{TELTONIKA_IP}/api/v1/modem/status",
            headers={"Authorization": f"Bearer {API_TOKEN}"},
            timeout=5
        )
        if response.status_code == 401: # Token expired
            print("Token expired, re-authenticating.")
            get_teltonika_token()
            return get_modem_status() # Retry once

        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"Error getting modem status: {e}")
        return None
