import asyncio
import logging
import math

import board  # type: ignore
import busio  # type: ignore
import serial
from adafruit_bmp3xx import BMP3XX_I2C  # type: ignore

from app.config import get_settings
from app.models import (
    HighFrequencyStateSensorBaroResponse,
    HighFrequencyStateSensorGpsResponse,
    SensorsInitResponse,
)

# Oversampling settings chosen as a trade-off between resolution and sample time:
# - Pressure: 8x for improved pressure resolution/stability (useful for altitude calc)
# - Temperature: 2x since temperature changes slowly and lower oversampling reduces conversion time
BMP388_PRESSURE_OVERSAMPLING = 8
BMP388_TEMPERATURE_OVERSAMPLING = 2

R_DRY = 287.05  # Specific gas constant for dry air (J/(kg·K))
G_STD = 9.80665  # Standard gravity (m/s²)
MINUTES_PER_DEGREE = 60.0
KNOTS_TO_KMH = 1.852
CELSIUS_TO_KELVIN = 273.15


async def init_sensors() -> SensorsInitResponse:
    """
    Initialize and calibrate the GPS and barometric sensors.

    This function attempts to connect to the GPS (via serial port) and the barometric sensor (via I2C)
    with infinite retry loops. It suspends execution until both sensors are successfully initialized.

    For the barometric sensor, it performs a calibration by collecting a number of pressure and temperature
    samples (as specified in the configuration) to compute reference values.
    """
    gps_port = get_settings().sensors.gps_serial_port
    gps_baudrate = get_settings().sensors.gps_baudrate
    baro_i2c_addr = get_settings().sensors.baro_i2c_address
    baro_ref_samples = get_settings().sensors.baro_reference_samples

    ser = None
    bmp = None
    p_ref = None
    t_ref = None

    # Try to initialize GPS up to 2 times
    for attempt in range(2):
        try:
            ser = serial.Serial(gps_port, gps_baudrate, timeout=2)
            logging.info(f"GPS on {gps_port}@{gps_baudrate} connected.")
            break
        except Exception as e:
            logging.warning(f"GPS initialization failed (attempt {attempt + 1}/2): {e}")
            await asyncio.sleep(1)

    # Try to initialize Barometric sensor up to 2 times
    for attempt in range(2):
        try:
            i2c = busio.I2C(board.SCL, board.SDA)
            bmp = BMP3XX_I2C(i2c, address=baro_i2c_addr)
            bmp.pressure_oversampling = BMP388_PRESSURE_OVERSAMPLING
            bmp.temperature_oversampling = BMP388_TEMPERATURE_OVERSAMPLING
            logging.info(f"BMP388 @ {hex(baro_i2c_addr)} | Calibrating reference...")
            p_samples: list[float] = []
            t_samples: list[float] = []
            for _ in range(baro_ref_samples):
                try:
                    p, t = bmp.pressure, bmp.temperature
                    if p is not None and t is not None:
                        p_samples.append(p)
                        t_samples.append(t)
                except Exception:
                    logging.exception("Exception while reading BMP388 sensor")
                await asyncio.sleep(0.1)
            if p_samples and t_samples:
                p_ref = sum(p_samples) / len(p_samples)
                t_ref = sum(t_samples) / len(t_samples)
                logging.info(f"Reference: p={p_ref:.2f} hPa, t={t_ref:.2f}°C")
                break
            else:
                logging.warning(
                    f"Barometric sensor calibration failed: no valid samples. (attempt {attempt + 1}/2)"
                )
        except Exception as e:
            logging.warning(
                f"Barometric sensor initialization failed (attempt {attempt + 1}/2): {e}"
            )
            await asyncio.sleep(1)

    return SensorsInitResponse(
        gps_serial_instance=ser,
        bmp3xx_driver=bmp,
        p_ref_hpa=p_ref,
        t_ref_celsius=t_ref,
    )


def nmea_coord_to_decimal(coord_str, hemi) -> float | None:
    """
    Convert an NMEA coordinate string to decimal degrees.

    Parameters:
        coord_str (str): Coordinate in NMEA format as a string.
            For latitude: "ddmm.mmmm" (degrees and minutes).
            For longitude: "dddmm.mmmm" (degrees and minutes).
        hemi (str): Hemisphere indicator, one of "N", "S", "E", or "W".
            "N" and "E" yield positive values, "S" and "W" yield negative values.

    Returns:
        float or None: The coordinate in decimal degrees, or None if input is invalid.
    """

    if not coord_str:
        return None
    try:
        dot = coord_str.find(".")
        if dot == -1:
            return None
        if hemi in ("N", "S"):
            deg_len = 2
        elif hemi in ("E", "W"):
            deg_len = 3
        else:
            return None
        deg = float(coord_str[:deg_len])
        minutes = float(coord_str[deg_len:])
        dec = deg + minutes / MINUTES_PER_DEGREE
        if hemi in ("S", "W"):
            dec = -dec
        return dec
    except (ValueError, IndexError):
        return None


def parse_nmea(line) -> HighFrequencyStateSensorGpsResponse | None:
    """
    Parse an NMEA sentence and extract relevant GPS information.

    Supports the following NMEA sentence types:
        - RMC: Recommended Minimum Specific GPS/Transit Data
        - GGA: Global Positioning System Fix Data

    For RMC sentences, extracts:
        - GPS fix status
        - Latitude and longitude (converted to decimal degrees)
        - Speed over ground (converted to km/h)

    For GGA sentences, extracts:
        - GPS fix status
        - Number of satellites in view
        - Altitude above mean sea level (in meters)
    """
    if not line.startswith("$"):
        return None
    parts = line.split("*")[0].strip().split(",")
    msg_type = parts[0][3:]
    if msg_type == "RMC" and len(parts) > 9:
        try:
            speed_kmh = float(parts[7]) * KNOTS_TO_KMH if parts[7] else None
        except ValueError:
            speed_kmh = None

        return HighFrequencyStateSensorGpsResponse(
            gps_fix=(parts[2] == "A") if parts[2] else None,
            latitude=nmea_coord_to_decimal(parts[3], parts[4]),
            longitude=nmea_coord_to_decimal(parts[5], parts[6]),
            speed_kmh=speed_kmh,
        )
    elif msg_type == "GGA" and len(parts) > 9:
        try:
            alt_m = float(parts[9]) if parts[9] else None
        except ValueError:
            alt_m = None
        return HighFrequencyStateSensorGpsResponse(
            gps_fix=(parts[6] != "0") if parts[6] else None,
            satellites=int(parts[7]) if parts[7].isdigit() else None,
            gps_altitude=alt_m,
        )
    return None


def rel_altitude_m(p_hpa, p_ref_hpa, t_cur_c, t_ref_c) -> float | None:
    """
    Calculate the relative altitude (in meters) between two pressure and temperature readings
    using the barometric (hypsometric) formula.

    The hypsometric equation relates the difference in altitude to the ratio of atmospheric
    pressures and the mean temperature of the air column:

        Δh = (R_d * T_mean) / g * ln(p_ref / p)

    where:
        Δh      = relative altitude in meters
        R_d     = specific gas constant for dry air (R_DRY = 287.05 J/(kg·K))
        T_mean  = mean temperature in Kelvin between the two measurements
        g       = standard gravity (G_STD = 9.80665 m/s²)
        p_ref   = reference pressure in hPa
        p       = current pressure in hPa
    """
    if p_hpa <= 0 or p_ref_hpa <= 0:
        return None
    t_mean_k = ((t_cur_c + t_ref_c) / 2.0) + CELSIUS_TO_KELVIN
    return (R_DRY * t_mean_k / G_STD) * math.log(p_ref_hpa / p_hpa)


async def gps_read(ser: serial.Serial) -> HighFrequencyStateSensorGpsResponse:
    """
    Reads a line from the provided serial port, attempts to parse it as a GPS NMEA sentence,
    and returns a HighFrequencyStateSensorGpsResponse object if successful.
    """
    try:
        line = ser.readline().decode(errors="ignore")
        if not line:
            return HighFrequencyStateSensorGpsResponse()
        parsed = parse_nmea(line)
        if parsed:
            return parsed
    except serial.SerialException:
        logging.exception("Error reading from GPS serial port.")
    return HighFrequencyStateSensorGpsResponse()


async def baro_read(
    bmp3xx_driver: BMP3XX_I2C, p_ref: float, t_ref: float
) -> HighFrequencyStateSensorBaroResponse:
    """
    Reads the current pressure and temperature from the BMP3XX barometric sensor,
    computes the relative altitude with respect to a reference pressure and temperature,
    and returns the results in a HighFrequencyStateSensorBaroResponse object.
    """
    try:
        p_cur, t_cur = bmp3xx_driver.pressure, bmp3xx_driver.temperature
        if p_cur is not None and t_cur is not None:
            delta_h = rel_altitude_m(p_cur, p_ref, t_cur, t_ref)
            return HighFrequencyStateSensorBaroResponse(
                pressure_hpa=round(p_cur, 2),
                temperature_celsius=round(t_cur, 2),
                baro_relative_altitude=round(delta_h, 2) if delta_h is not None else None,
            )
    except Exception:
        logging.exception("Failed to read pressure/temperature from BMP388 sensor.")
    return HighFrequencyStateSensorBaroResponse()
