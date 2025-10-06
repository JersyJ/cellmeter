# CellMeter

📡 **CellMeter** is a drone-based platform for measuring, storing, and visualizing **cellular signal quality** and **network performance**.  
It polls a Teltonika OTD500 every second, stores telemetry locally in **InfluxDB** on the drone, and forwards it in **real time** to a ground station for Grafana dashboards and monitoring.

---

## Features
- Near real-time (1s) data collection from **Teltonika OTD500 JSON API**  
- Metrics: GPS, altitude, RSSI, RSRP, RSRQ, SINR, CID/PCI, download/upload speed  
- **Session-based measuring** with unique IDs and timestamps  
- Permanent storage of historical data (InfluxDB)  
- Interactive dashboards in Grafana  

---

## Architecture

![Architecture](architecture.drawio.svg)