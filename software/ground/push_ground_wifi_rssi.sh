#!/usr/bin/env bash
# Collect Wi-Fi RSSI and push to InfluxDB.
# Usage: push_ground_wifi_rssi.sh [iface]

set -uo pipefail   # <-- -e removed so iw failures don't kill cron
PATH=/usr/sbin:/usr/bin:/bin

IFACE=${1:-wlan1}
ORG="cellmeter-org"
BUCKET="metrics"
HOST="http://localhost:8086"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

ENV_FILE="$SCRIPT_DIR/.env"
if [ -f "$ENV_FILE" ]; then
  set -a
  . "$ENV_FILE"
  set +a
fi

TOKEN="${DATABASE__TOKEN:-REPLACE_WITH_GROUND_INFLUX_TOKEN}"

LOG=/tmp/wifi_rssi_debug.log

# Try RSSI from link (STA mode)
RSSI=$(/usr/sbin/iw dev "$IFACE" link 2>&1 | /usr/bin/awk '/signal:/ {print $2}') || true

# Try station dump (AP mode)
if [ -z "${RSSI:-}" ]; then
  RSSI=$(/usr/sbin/iw dev "$IFACE" station dump 2>&1 | /usr/bin/awk '/signal:/ {print $2; exit}') || true
fi

echo "$(date -Iseconds) iface=$IFACE rssi=${RSSI:-nil}" >> "$LOG"

# If still nothing, exit cleanly
[ -z "${RSSI:-}" ] && exit 0

DATA="ground_wifi,host=ground,iface=${IFACE} rssi_dbm=${RSSI}"

HTTP_CODE=$(/usr/bin/curl -s -o /tmp/wifi_rssi_curl.out -w "%{http_code}" \
  -X POST "${HOST}/api/v2/write?org=${ORG}&bucket=${BUCKET}&precision=s" \
  -H "Authorization: Token ${TOKEN}" \
  --data-binary "$DATA")

echo "$(date -Iseconds) http_code=$HTTP_CODE data=$DATA" >> "$LOG"
