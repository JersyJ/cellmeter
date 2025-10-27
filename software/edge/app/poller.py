import logging

import httpx

from app.config import get_settings
from app.models import HighFrequencyStateTeltonikaResponse

API_TOKEN = None


async def get_teltonika_token():
    """Authenticates with Teltonika and gets a session token."""
    global API_TOKEN
    try:
        async with httpx.AsyncClient(verify=not get_settings().debug_mode) as client:
            response = await client.post(
                f"https://{get_settings().teltonika.ip}/api/login",
                headers={"Content-Type": "application/json"},
                json={
                    "username": get_settings().teltonika.user,
                    "password": get_settings().teltonika.password.get_secret_value(),
                },
                timeout=5,
            )
            response.raise_for_status()
            data = response.json()
            if data.get("success") and "data" in data and "token" in data["data"]:
                API_TOKEN = data["data"]["token"]
                logging.info("Successfully authenticated with Teltonika.")
    except httpx.RequestError:
        logging.exception("Error authenticating with Teltonika")


async def get_modem_status() -> HighFrequencyStateTeltonikaResponse | None:
    """Polls the modem status endpoint for cellular and GPS data."""
    global API_TOKEN
    if not API_TOKEN:
        logging.info("No auth token, attempting to re-authenticate.")
        await get_teltonika_token()
        if not API_TOKEN:
            return None

    try:
        async with httpx.AsyncClient(verify=not get_settings().debug_mode) as client:
            response = await client.get(
                f"https://{get_settings().teltonika.ip}/api/v1/modems/status",
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {API_TOKEN}",
                },
                timeout=5,
            )
            if response.status_code == 401:  # Token expired
                logging.info("Token expired, re-authenticating.")
                await get_teltonika_token()
                return await get_modem_status()  # Retry once

            response.raise_for_status()
            return HighFrequencyStateTeltonikaResponse.model_validate(response.json())
    except httpx.RequestError as e:
        logging.exception(f"Error getting modem status: {e}")
        return None
