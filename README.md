# CellMeter

📡 **CellMeter** is a drone-based platform for measuring, storing, and visualizing **cellular signal quality** and **network performance**.

It polls data from the **Teltonika OTD500 API**, including **GPS** and **altimeter** readings, stores it locally in InfluxDB Edge on the drone, and replicates it in real time to the InfluxDB instance on the ground station, which provides Grafana dashboards and monitoring.

---

## Features
- Two types of data collection from **Teltonika OTD500 JSON API** and other sensors
- Metrics: GPS, altitude, RSSI, RSRP, RSRQ, SINR, CID/PCI, download/upload speed
- **Session-based measuring** with unique IDs and timestamps
- Permanent storage of historical data (InfluxDB)
- Interactive dashboards in Grafana

---

## SW Architecture

![SW Architecture](docs/architecture-sw.svg)

## HW Architecture & System Configuration

[HW Architecture & System Configuration Documentation](docs/system_conf.md)

## Data Collection Strategy

[Data Collection Strategy Documentation](docs/data-collection-strategy.md)
