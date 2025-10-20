from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS
import os

INFLUX_URL = os.getenv("INFLUX_URL_EDGE", "http://localhost:8086")
INFLUX_TOKEN = os.getenv("INFLUX_TOKEN_EDGE") # The token for the local InfluxDB
INFLUX_ORG = os.getenv("INFLUX_ORG", "cellmeter-org")
INFLUX_BUCKET = os.getenv("INFLUX_BUCKET", "raw-data")

client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
write_api = client.write_api(write_options=SYNCHRONOUS)

def write_state_metrics(session_id, iccid, data):
    """Writes the high-frequency state metrics to InfluxDB."""
    point = (
        Point("state_metrics")
        .tag("session_id", session_id)
        .tag("iccid", iccid)
        .tag("operator", data.get("operator"))
        .tag("network_type", data.get("network_type"))
        .tag("cell_id", data.get("cell_id"))
        .field("rsrp", data.get("rsrp", 0))
        .field("rsrq", data.get("rsrq", 0))
        .field("sinr", data.get("sinr", 0))
        .field("latitude", data.get("latitude", 0.0))
        .field("longitude", data.get("longitude", 0.0))
        .field("altitude", data.get("altitude", 0.0))
        .field("modem_temperature", data.get("temperature", 0.0))
    )
    write_api.write(bucket=INFLUX_BUCKET, record=point)

# TODO: add performance benchmarks later
# def write_performance_benchmark(...)