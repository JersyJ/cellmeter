from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS

from app.config import get_settings

client = InfluxDBClient(
    url=get_settings().database.url,
    token=get_settings().database.token.get_secret_value(),
    org=get_settings().database.org,
)
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
    write_api.write(bucket=get_settings().database.bucket, record=point)


# TODO: add performance benchmarks later
# def write_performance_benchmark(...)
