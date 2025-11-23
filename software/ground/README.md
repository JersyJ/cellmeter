# Ground Station Monitoring Stack

Monitoring stack for Ground Station with InfluxDB and Grafana.

## Quick Start

```bash
docker compose up -d
```

## Access

- **Grafana**: http://localhost:3000 (admin/admin123)
- **InfluxDB UI**: http://localhost:8086 (admin/P@ssw0rd!)
- **InfluxDB API**: http://localhost:8086

## Configuration

Before starting, create `.env` file from the example:

```bash
cp .env.example .env
```

Edit `.env` and set your values:
- `DATABASE__TOKEN` - InfluxDB access token
- Organization: `cellmeter-org`
- Bucket: `metrics`

## Usage

### Writing Data (InfluxDB Line Protocol)

```bash
# Using InfluxDB v2 API
curl -X POST "http://localhost:8086/api/v2/write?org=cellmeter-org&bucket=metrics" \
  -H "Authorization: Token testingToken123" \
  --data-raw "temperature,sensor=ground_station value=23.5"
```

### Querying Data (Flux)

```bash
influx query 'from(bucket: "metrics") |> range(start: -1h)' \
  --host http://localhost:8086 \
  --token testingToken123 \
  --org cellmeter-org
```

## Management

```bash
docker compose logs -f              # Show logs
docker compose stop                 # Stop services
docker compose start                # Start services
docker compose restart              # Restart services
docker compose down                 # Stop and remove containers
docker compose down -v              # Remove including data volumes
```

## Dashboard

The **"Cellmeter - Drone Telemetry"** dashboard is automatically provisioned and includes:
- Radio signal quality (RSRP, RSRQ, SINR)
- GPS tracking and altitude
- Environmental sensors (temperature, pressure)
- Network performance metrics

## Links

- [InfluxDB docs](https://docs.influxdata.com/influxdb/v2/)
- [Grafana docs](https://grafana.com/docs/)
