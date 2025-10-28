import logging

from influxdb_client.client.influxdb_client_async import InfluxDBClientAsync
from influxdb_client.client.write.point import Point

from app.config import get_settings
from app.models import (
    HighFrequencyStateTeltonikaResponse,
    Iperf3Result,
    PingResult,
    SpeedtestResult,
)

client = InfluxDBClientAsync(
    url=get_settings().database.url,
    token=get_settings().database.token.get_secret_value(),
    org=get_settings().database.org,
)
write_api = client.write_api()


async def write_state_metrics(session_id, iccid, data: HighFrequencyStateTeltonikaResponse):
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
    await write_api.write(
        bucket=get_settings().database.bucket, org=get_settings().database.org, record=point
    )
    logging.debug("Wrote state metrics to InfluxDB.")


async def write_performance_benchmark(
    session_id: str,
    iccid: str | None,
    test_type: str,
    data: PingResult | Iperf3Result | SpeedtestResult,
):
    point = (
        Point("performance_benchmarks")
        .tag("session_id", session_id)
        .tag("iccid", iccid)
        .tag("test_type", test_type)
    )
    for field, value in data.model_dump().items():
        if value is not None:
            point.field(field, value)

    if len(point._fields) != 0:
        await write_api.write(bucket=get_settings().database.bucket, record=point)
        logging.info(f"Wrote '{test_type}' benchmark to InfluxDB.")
