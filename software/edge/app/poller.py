import logging

import requests

from app.config import get_settings
from app.models import HighFrequencyStateTeltonikaResponse

API_TOKEN = None


def get_teltonika_token():
    """Authenticates with Teltonika and gets a session token."""
    global API_TOKEN
    try:
        response = requests.post(
            f"https://{get_settings().teltonika.ip}/api/login",
            headers={"Content-Type": "application/json"},
            json={
                "username": get_settings().teltonika.user,
                "password": get_settings().teltonika.password.get_secret_value(),
            },
            timeout=5,
            verify=False if get_settings().debug_mode else None,  # Teltonika uses self-signed certs
        )
        response.raise_for_status()
        data = response.json()
        if data.get("success") and "data" in data and "token" in data["data"]:
            API_TOKEN = data["data"]["token"]
            logging.info("Successfully authenticated with Teltonika.")
    except requests.RequestException:
        logging.exception("Error authenticating with Teltonika")


def get_modem_status() -> HighFrequencyStateTeltonikaResponse | None:
    """Polls the modem status endpoint for cellular and GPS data."""
    if not API_TOKEN:
        logging.info("No auth token, attempting to re-authenticate.")
        get_teltonika_token()
        if not API_TOKEN:
            return None

    try:
        response = requests.get(
            f"https://{get_settings().teltonika.ip}/api/v1/modems/status",
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {API_TOKEN}"},
            timeout=5,
            verify=False if get_settings().debug_mode else None,  # Teltonika uses self-signed certs
        )
        if response.status_code == 401:  # Token expired
            logging.info("Token expired, re-authenticating.")
            get_teltonika_token()
            return get_modem_status()  # Retry once

        response.raise_for_status()
        return HighFrequencyStateTeltonikaResponse.model_validate(response.json())
    except requests.RequestException as e:
        logging.exception(f"Error getting modem status: {e}")
