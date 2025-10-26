from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS

from app.config import get_settings
from app.models import HighFrequencyStateTeltonikaResponse

client = InfluxDBClient(
    url=get_settings().database.url,
    token=get_settings().database.token.get_secret_value(),
    org=get_settings().database.org,
)
write_api = client.write_api(write_options=SYNCHRONOUS)


def write_state_metrics(session_id, iccid, data: HighFrequencyStateTeltonikaResponse):
    """Writes the high-frequency state metrics to InfluxDB."""
    point = (
        Point("state_metrics")
        .tag("session_id", session_id)
        .tag("iccid", iccid)
        .tag("operator", data.operator)
        .tag("network_type", data.network_type)
        .tag("cell_id", data.cell_id)
        .field("rsrp", data.rsrp)
        .field("rsrq", data.rsrq)
        .field("sinr", data.sinr)
        .field("latitude", None)  # TODO: Placeholder, as GPS data is not in the current model
        .field("longitude", None)  # TODO: Placeholder, as GPS data is not in the current model
        .field("altitude", None)  # TODO: Placeholder, as GPS data is not in the current model
        .field("modem_temperature", data.modem_temperature)
    )
    write_api.write(
        bucket=get_settings().database.bucket, org=get_settings().database.org, record=point
    )


# TODO: add performance benchmarks later
# def write_performance_benchmark(...)
