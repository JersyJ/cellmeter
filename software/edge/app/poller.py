import asyncio
import json
import logging
import re

import httpx

from app.config import get_settings
from app.models import (
    HighFrequencyStateTeltonikaResponse,
    Iperf3Result,
    PingResult,
    SpeedtestResult,
)
from app.ssh_client import ssh_client

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
            return HighFrequencyStateTeltonikaResponse.model_validate_json(response.text)
    except httpx.RequestError as e:
        logging.exception(f"Error getting modem status: {e}")
        return None


async def run_ssh_ping() -> PingResult | None:
    """Runs ping via SSH on the Teltonika device."""
    command = f"ping -c {get_settings().benchmarking.ping_count} {get_settings().benchmarking.ping_address}"
    logging.info(f"Running ping test via SSH: {command}")
    output = await ssh_client.execute_command(command, timeout=15)
    if not output:
        return None
    try:
        rtt_match = re.search(
            r"(?:rtt|round-trip) min/avg/max(?:/mdev)? = [\d.]+/([\d.]+)/", output
        )
        loss_match = re.search(r"(\d+)% packet loss", output)
        return PingResult(
            rtt_avg_ms=float(rtt_match.group(1)) if rtt_match else None,
            packet_loss_pct=float(loss_match.group(1)) if loss_match else None,
        )
    except Exception:
        logging.exception("Error running ping output")
        return None


async def run_ssh_iperf3() -> Iperf3Result | None:
    """Runs iperf3 tests via SSH on the Teltonika device using JSON output."""
    server_ip = get_settings().benchmarking.iperf3_server_ip
    logging.info(f"Running iperf3 tests via SSH to {server_ip}")
    results = {}
    upload_output = await ssh_client.execute_command(f"iperf3 -c {server_ip} -f m --json", 30)
    download_output = await ssh_client.execute_command(f"iperf3 -c {server_ip} -f m -R --json", 30)
    jitter_output = await ssh_client.execute_command(f"iperf3 -c {server_ip} -u -b 10M --json", 30)
    try:
        if upload_output:
            results["upload_mbps"] = (
                json.loads(upload_output)["end"]["sum_sent"]["bits_per_second"] / 1e6
            )
        if download_output:
            results["download_mbps"] = (
                json.loads(download_output)["end"]["sum_received"]["bits_per_second"] / 1e6
            )
        if jitter_output:
            results["jitter_ms"] = json.loads(jitter_output)["end"]["sum"]["jitter_ms"]
    except Exception:
        logging.exception("Error parsing iperf3 output")
        return None

    return Iperf3Result.model_validate(results)


async def run_teltonika_speedtest() -> SpeedtestResult | None:
    """Runs and monitors the Teltonika speedtest using its dedicated JSON API."""
    global API_TOKEN
    if not API_TOKEN:
        logging.info("No auth token, attempting to re-authenticate.")
        await get_teltonika_token()
        if not API_TOKEN:
            return None

    base_url = f"https://{get_settings().teltonika.ip}/api/speedtest"
    headers = {"Authorization": f"Bearer {API_TOKEN}"}

    logging.info("Starting speedtest via Teltonika API...")
    async with httpx.AsyncClient(verify=not get_settings().debug_mode) as client:
        # Step 1: Start the test
        start_res = await client.post(
            f"{base_url}/actions/start",
            headers=headers,
            json={
                "data": {
                    "url": get_settings().benchmarking.speedtest_url,
                }
            },
            timeout=10,
        )
        if start_res.status_code == 409:
            logging.warning("Speedtest is already running, will monitor for results.")
        elif not start_res.is_success:
            logging.error(f"Failed to start Teltonika speedtest: {start_res.text}")
            return None

        # Step 2: Poll for status and capture results
        for _ in range(120):  # Poll for a maximum of 2 minutes
            await asyncio.sleep(1)
            status_res = await client.get(f"{base_url}/status", headers=headers, timeout=10)
            data = status_res.json()
            state = str(data["data"]["state"]).upper()

            if state == "TESTING_DOWNLOAD":
                current_download = int(data["data"].get("avgDownloadSpeed", 0)) / 1_000_000
                if current_download > 0:
                    download_mbps = current_download
                logging.info(f"Speedtest in progress: {state} ({current_download:.2f} Mbps)")
                continue
            elif state == "TESTING_UPLOAD":
                current_upload = int(data["data"].get("avgUploadSpeed", 0)) / 1_000_000
                if current_upload > 0:
                    upload_mbps = current_upload
                logging.info(f"Speedtest in progress: {state} ({current_upload:.2f} Mbps)")
                continue
            elif state in ["NOT_RUNNING", "FINISHED"]:
                if state == "FINISHED":
                    download_mbps = int(data["data"].get("avgDownloadSpeed", 0)) / 1_000_000
                    upload_mbps = int(data["data"].get("avgUploadSpeed", 0)) / 1_000_000
                logging.info(f"Speedtest has finished with state: {state}.")
                break
            else:
                continue
        else:
            logging.error("Speedtest timed out after 120 seconds.")

        # Step 3: Return captured results
        if download_mbps is not None or upload_mbps is not None:
            return SpeedtestResult(download_mbps=download_mbps, upload_mbps=upload_mbps)
        else:
            logging.warning("Speedtest finished without capturing any results.")
            return None
