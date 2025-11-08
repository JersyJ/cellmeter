import logging

from influxdb_client.client.influxdb_client_async import InfluxDBClientAsync
from influxdb_client.client.write.point import Point

from app.config import get_settings
from app.models import (
    HighFrequencyStateSensorBaroResponse,
    HighFrequencyStateSensorGpsResponse,
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


async def write_state_metrics(
    session_id,
    iccid,
    teltonika_data: HighFrequencyStateTeltonikaResponse,
    gps_data: HighFrequencyStateSensorGpsResponse,
    baro_data: HighFrequencyStateSensorBaroResponse,
):
    """Writes the high-frequency state metrics to InfluxDB."""
    point = (
        Point("state_metrics")
        .tag("session_id", session_id)
        .tag("iccid", iccid)
        .tag("operator", teltonika_data.operator)
        .tag("network_type", teltonika_data.network_type)
        .tag("cell_id", teltonika_data.cell_id)
        .field("rsrp", teltonika_data.rsrp)
        .field("rsrq", teltonika_data.rsrq)
        .field("sinr", teltonika_data.sinr)
        .field("tracking_area_code", teltonika_data.tracking_area_code)
        .field("frequency_band", teltonika_data.frequency_band)
        .field("frequency_channel", teltonika_data.frequency_channel)
        .field("physical_cell_id", teltonika_data.physical_cell_id)
        .field("modem_temperature", teltonika_data.modem_temperature)
        .field("gps_fix", gps_data.gps_fix)
        .field("latitude", gps_data.latitude)
        .field("longitude", gps_data.longitude)
        .field("gps_altitude", gps_data.gps_altitude)
        .field("speed_kmh", gps_data.speed_kmh)
        .field("satellites", gps_data.satellites)
        .field("pressure_hpa", baro_data.pressure_hpa)
        .field("temperature_celsius", baro_data.temperature_celsius)
        .field("baro_relative_altitude", baro_data.baro_relative_altitude)
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
