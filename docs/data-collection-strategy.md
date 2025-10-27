# Data Collection Strategy

The strategy is divided into two primary categories:

1.  **High-Frequency State Monitoring:** Passively polling for radio quality and contextual device status at a high rate.
2.  **Low-Frequency Performance Benchmarking:** Actively running network tests to measure real-world performance at a lower rate.


## **Session Management**

To ensure data integrity and simplify analysis, all data collected during a specific operational flight or test run is grouped into a **Session**.

*   **Session Start:** A new session is initiated at the beginning of a data collection flight.
*   **Session Identifier (`session_id`):** Upon starting, a unique identifier (e.g., a UUID or a timestamp) is generated. This `session_id` is attached to every single data point recorded during the session.
*   **Contextual Data Logging:** At the beginning of each session, key contextual information is logged. This includes:
    *   **Active SIM ICCID:** A request is made to the Teltonika API (`GET /api/v1/sim/status`) to retrieve the ICCID of the currently active SIM card. This allows for precise tracking of which mobile carrier is being used for the duration of the session.

---

### **Group 1: High-Frequency State Monitoring**

This group combines radio layer metrics with the drone's physical and contextual data. These data points provide a comprehensive snapshot of the platform's state at any given moment.

*   **Execution Interval:** ~1 second (1 Hz)
*   **Methodology:** A background service on the onboard Raspberry Pi 5 will continuously poll the Teltonika REST API, GPS receiver, and the drone's flight controller (if available) to gather these metrics. Each set of readings will be written to the InfluxDB `state_metrics` measurement with a unified timestamp and the session's `session_id`.

#### **Data Points to Collect (per 1-second interval):**

| Parameter Name | Method/Acronym | Source | Description |
| :--- | :--- | :--- | :--- |
| **Radio Layer** | | | |
| `rsrp` | RSRP | Teltonika API `GET /api/v1/modem/status` | **Reference Signal Received Power.** Primary metric for signal strength (in dBm). |
| `rsrq` | RSRQ | Teltonika API `GET /api/v1/modem/status` | **Reference Signal Received Quality.** Indicates signal quality considering interference. |
| `sinr` | SINR | Teltonika API `GET /api/v1/modem/status` | **Signal-to-Interference-plus-Noise Ratio.** Key indicator of link speed/throughput. |
| **Network Identity** | | |
| `cell_id` | CID / ECI | Teltonika API `GET /api/v1/modem/status` | The unique ID of the connected cell tower (BTS). Essential for mapping and handover detection. |
| `tracking_area_code` | TAC | Teltonika API `GET /api/v1/modem/status` | Tracking Area Code; a group of cells the BTS belongs to. |
| `network_type` | Network Type | Teltonika API `GET /api/v1/modem/status` | The type of network connection (e.g., `LTE`, `NR5G`). |
| `frequency_band` | Frequency Band | Teltonika API `GET /api/v1/modem/status` | The specific frequency band being used. |
| `frequency_channel` | EARFCN / NR-ARFCN | Teltonika API `GET /api/v1/modem/status` | Radio Frequency Channel Number for precise cell identification. |
| `physical_cell_id` | PCI | Teltonika API `GET /api/v1/modem/status` | Physical Cell ID used for signal synchronization (4G/5G). |
| `operator` | PLMN (MCC,MNC) |Teltonika API `GET /api/v1/modem/status` | The name and PLMN code of the mobile network operator. |
| **Positional & Kinematic Data** | | | |
| `latitude` | Lat | GPS | **Latitude.** Geographic coordinate specifying north–south position. |
| `longitude` | Lon | GPS | **Longitude.** Geographic coordinate specifying east–west position. |
| `altitude` | Alt | Altimeter / GPS | **Altitude.** Height above sea level (meters). |
| `ground_speed` | GS | GPS | **Ground Speed.** Drone's speed over ground (meters/second). |
| **Device Status** | | | |
| `modem_temperature` | Temp | Teltonika API `GET /api/v1/modem/status` | **Modem Temperature.** Internal temperature of the modem (°C). Useful for diagnosing performance throttling. |

---

### **Group 2: Low-Frequency Performance Benchmarking**

This group consists of active network tests that measure the actual user experience (throughput, latency, reliability). They are run less frequently to minimize network load and data consumption.

*   **Execution Interval:** ~30 - 60 seconds
*   **Methodology:** The onboard service will periodically execute command-line tools (`iperf3`, `ping`, `speedtest-cli`). The parsed results will be written to the InfluxDB `performance_benchmarks` measurement, tagged with the session's `session_id`.

#### **Data Points to Collect (per 30-60 second interval):**

| Parameter Name | Tool | Description |
| :--- | :--- | :--- |
| **Throughput** | | |
| `iperf3_upload_mbps` | `iperf3` | Measured upload bandwidth to your dedicated server. |
| `iperf3_download_mbps`| `iperf3 -R` | Measured download bandwidth from your dedicated server. |
| `speedtest_upload_mbps`| `speedtest-cli` | Measured upload bandwidth to a public SpeedTest server. (Run less often, e.g., every 5 min). |
| `speedtest_download_mbps`| `speedtest-cli` | Measured download bandwidth from a public SpeedTest server. (Run less often). |
| **Latency & Reliability** | | |
| `ping_rtt_avg_ms` | `ping` | Average Round Trip Time to a stable target (e.g., `8.8.8.8` or ground server). |
| `ping_packet_loss_pct`| `ping` | Percentage of lost packets during the ping test. |
| **Jitter** | | |
| `iperf3_jitter_ms` | `iperf3 -u` | Jitter (variation in latency) measured during a UDP test. Critical for real-time applications. |

---

## **InfluxDB Schema**

Primary tags are `session_id` and `iccid` to ensure all data can be easily queried and grouped by a specific test session and carrier.

**1. High-Frequency Measurement:** `state_metrics`
*   **Tags (for filtering/grouping):** `session_id`, `iccid`, `operator`, `network_type`, `cell_id`
*   **Fields (the values):** `rsrp`, `rsrq`, `sinr`, `latitude`, `longitude`, `altitude`, `ground_speed`, `modem_temperature`, `physical_cell_id`, `tracking_area_code`

**Example (Line Protocol):**
```
state_metrics,session_id=flight-20251013-1030,iccid=8944100000000000001F,operator=Vodafone,network_type=NR5G,cell_id=123456 rsrp=-85,rsrq=-10,sinr=18,latitude=49.195,longitude=16.606,altitude=250.5,ground_speed=10.2,modem_temperature=55.2,physical_cell_id=110,tracking_area_code=3001 1697200200000000000
```

**2. Low-Frequency Measurement:** `performance_benchmarks`
*   **Tags (for filtering/grouping):** `session_id`, `iccid`, `test_type` (e.g., "iperf3", "ping", "speedtest")
*   **Fields (the values):** `upload_mbps`, `download_mbps`, `ping_rtt_avg_ms`, `ping_packet_loss_pct`, `jitter_ms`

**Example (Line Protocol):**
```
performance_benchmarks,session_id=flight-20251013-1030,iccid=8944100000000000001F,test_type=iperf3 upload_mbps=45.5,download_mbps=110.2,jitter_ms=5.8 1697200230000000000
performance_benchmarks,session_id=flight-20251013-1030,iccid=8944100000000000001F,test_type=ping ping_rtt_avg_ms=35.2,ping_packet_loss_pct=0 1697200235000000000
```
