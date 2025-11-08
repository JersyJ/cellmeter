import logging
import math
import time

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

R_DRY = 287.05
G_STD = 9.80665


def init_sensors():
    gps_port = get_settings().sensors.gps_serial_port
    gps_baudrate = get_settings().sensors.gps_baudrate
    baro_i2c_addr = get_settings().sensors.baro_i2c_address
    baro_ref_samples = get_settings().sensors.baro_reference_samples

    while True:
        try:
            ser = serial.Serial(gps_port, gps_baudrate, timeout=2)
            logging.info(f"GPS on {gps_port}@{gps_baudrate} connected.")
            break
        except serial.SerialException as e:
            logging.exception(f"Error GPS on {gps_port}: {e}. Next try in 3s...")
            time.sleep(3)

    while True:
        try:
            i2c = busio.I2C(board.SCL, board.SDA)
            bmp = BMP3XX_I2C(i2c, address=baro_i2c_addr)
            bmp.pressure_oversampling, bmp.temperature_oversampling = 8, 2
            logging.info(f"BMP388 @ {hex(baro_i2c_addr)} | Calibrating reference...")
            p_samples, t_samples = [], []
            while len(p_samples) < baro_ref_samples:
                try:
                    p, t = bmp.pressure, bmp.temperature
                    if p is not None and t is not None:
                        p_samples.append(p)
                        t_samples.append(t)
                except Exception:
                    pass
                time.sleep(0.1)
            p_ref, t_ref = sum(p_samples) / len(p_samples), sum(t_samples) / len(t_samples)
            logging.info(f"Reference: p={p_ref:.2f} hPa, t={t_ref:.2f}°C")
            break
        except (ValueError, RuntimeError) as e:
            logging.exception(f"Error BMP388 on {hex(baro_i2c_addr)}: {e}. Next try in 3s...")
            time.sleep(3)

    return SensorsInitResponse(
        gps_serial_instance=ser,
        bmp3xx_driver=bmp,
        p_ref_hpa=p_ref,
        t_ref_celsius=t_ref,
    )


def nmea_coord_to_decimal(coord_str, hemi):
    if not coord_str:
        return None
    try:
        dot = coord_str.find(".")
        if dot == -1:
            return None
        deg_len = dot - 2
        deg = float(coord_str[:deg_len])
        minutes = float(coord_str[deg_len:])
        dec = deg + minutes / 60.0
        if hemi in ("S", "W"):
            dec = -dec
        return dec
    except (ValueError, IndexError):
        return None


def parse_nmea(line) -> HighFrequencyStateSensorGpsResponse | None:
    if not line.startswith("$"):
        return None
    parts = line.split("*")[0].strip().split(",")
    msg_type = parts[0][3:]
    if msg_type == "RMC" and len(parts) > 9:
        try:
            speed_kmh = float(parts[7]) * 1.852 if parts[7] else None
        except ValueError:
            speed_kmh = None

        return HighFrequencyStateSensorGpsResponse(
            gps_fix=(parts[2] == "A") or None,
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
            gps_fix=(parts[6] != "0") or None,
            satellites=int(parts[7]) if parts[7].isdigit() else None,
            gps_altitude=alt_m,
        )
    return None


def rel_altitude_m(p_hpa, p_ref_hpa, t_cur_c, t_ref_c):
    if p_hpa <= 0 or p_ref_hpa <= 0:
        return None
    t_mean_k = ((t_cur_c + t_ref_c) / 2.0) + 273.15
    return (R_DRY * t_mean_k / G_STD) * math.log(p_ref_hpa / p_hpa)


def gps_read(ser: serial.Serial) -> HighFrequencyStateSensorGpsResponse | None:
    try:
        line = ser.readline().decode(errors="ignore")
        if not line:
            return None
        parsed = parse_nmea(line)
        if parsed:
            return parsed
    except serial.SerialException:
        logging.exception("Error GPS.")
    return None


def baro_read(
    bmp3xx_driver: BMP3XX_I2C, p_ref: float, t_ref: float
) -> HighFrequencyStateSensorBaroResponse | None:
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
        logging.exception("Error BMP388.")
    return None
