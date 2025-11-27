# InfluxDB Replication Setup

Automatic replication from edge station to ground station using InfluxDB.

## Quick Setup

### 1. Ground Station

On your ground station machine:

```bash
cd software/ground
cp .env.example .env
# Edit .env - set DATABASE__TOKEN to something secure
docker compose up -d
```

**Note the IP address** of this ground station machine (you'll need it for the edge station).

### 2. Edge Station

On your edge station machine:

```bash
cd software/edge
cp .env.example .env
```

# Edit `.env` and uncomment/set these lines:
```bash
GROUND_DATABASE__URL=http://YOUR_GROUND_STATION_IP:8086
GROUND_DATABASE__TOKEN=testingToken123
```
(Replace `YOUR_GROUND_STATION_IP` with the actual IP, e.g., `192.168.1.100`)

Start it:
```bash
docker compose up -d
```

### 3. Verify

```bash
docker compose logs replication-setup
```

Should show: "Replication setup complete!"

## Access

- **Grafana**: `http://GROUND_STATION_IP:3000` - Can see the dashboard without login
- **Edge InfluxDB**: `http://EDGE_STATION_IP:8086`
- **Ground InfluxDB**: `http://GROUND_STATION_IP:8086`

## Default Credentials

- You can find default credentials in .env

## Network Requirements

**Firewall Rules:**
- Ground station must allow incoming connections on port **8086** (InfluxDB)
- Ground station must allow incoming connections on port **3000** (Grafana)
- Edge station must be able to reach ground station IP

**Test connectivity from edge station:**
```bash
ping GROUND_STATION_IP
curl http://GROUND_STATION_IP:8086/health
```

## Troubleshooting

**Replication setup failed?**
- Check ground station is reachable: `ping GROUND_STATION_IP`
- Verify firewall allows port 8086
- Check tokens match on both stations
- View logs: `docker compose logs replication-setup`

**No data in Grafana?**
- Wait a few minutes for initial replication
- Verify edge station is collecting data
- Check replication status: `docker compose logs replication-setup`
