#!/bin/bash
set -e

echo "Waiting for InfluxDB to be ready..."
until influx ping --host $INFLUX_HOST; do
  echo "InfluxDB not ready, waiting..."
  sleep 2
done
echo "InfluxDB is ready!"

if [ -z "$GROUND_INFLUX_URL" ]; then
  echo "GROUND_DATABASE__URL not set, skipping replication setup"
  echo "To enable replication, set GROUND_DATABASE__URL and GROUND_DATABASE__TOKEN in .env"
  exit 0
fi

echo "Setting up replication to ground station..."
echo "Ground URL: $GROUND_INFLUX_URL"

# Get remote org ID
echo "Fetching remote organization ID..."
REMOTE_ORG_ID=$(curl -s "$GROUND_INFLUX_URL/api/v2/orgs?org=$INFLUX_ORG" \
  -H "Authorization: Token $GROUND_INFLUX_TOKEN" | \
  awk -F'"' '/"id":/ {print $4; exit}')

if [ -z "$REMOTE_ORG_ID" ]; then
  echo "Error: Could not get remote org ID from ground station"
  echo "Make sure the ground station is running and accessible"
  exit 1
fi

echo "Remote Org ID: $REMOTE_ORG_ID"

# Delete existing remote if it exists
echo "Cleaning up existing remote connection (if any)..."
EXISTING_REMOTE_ID=$(influx remote list --host $INFLUX_HOST --token $INFLUX_TOKEN --org $INFLUX_ORG --json 2>/dev/null | awk -F'"' '/"id":/ {print $4; exit}')
if [ -n "$EXISTING_REMOTE_ID" ]; then
  echo "Deleting existing remote ID: $EXISTING_REMOTE_ID"
  influx remote delete --id "$EXISTING_REMOTE_ID" \
    --host "$INFLUX_HOST" --token "$INFLUX_TOKEN" 2>/dev/null || true
fi

# Create remote connection
echo "Creating remote connection..."
influx remote create \
  --name "ground-station" \
  --remote-url "$GROUND_INFLUX_URL" \
  --remote-api-token "$GROUND_INFLUX_TOKEN" \
  --remote-org-id "$REMOTE_ORG_ID" \
  --org "$INFLUX_ORG" \
  --host "$INFLUX_HOST" \
  --token "$INFLUX_TOKEN"

# Get remote ID
REMOTE_ID=$(influx remote list --host $INFLUX_HOST --token $INFLUX_TOKEN --org $INFLUX_ORG --json | awk -F'"' '/"id":/ {print $4; exit}')

# Get bucket ID
BUCKET_ID=$(influx bucket list --host $INFLUX_HOST --token $INFLUX_TOKEN --org $INFLUX_ORG --name $INFLUX_BUCKET --json | awk -F'"' '/"id":/ {print $4; exit}')

if [ -z "$REMOTE_ID" ] || [ -z "$BUCKET_ID" ]; then
  echo "Error: Could not get remote ID or bucket ID"
  exit 1
fi

echo "Remote ID: $REMOTE_ID"
echo "Bucket ID: $BUCKET_ID"

# Delete existing replication if it exists
echo "Cleaning up existing replication (if any)..."
EXISTING_REPL_ID=$(influx replication list --host $INFLUX_HOST --token $INFLUX_TOKEN --org $INFLUX_ORG --json 2>/dev/null | awk -F'"' '/"id":/ {print $4; exit}')
if [ -n "$EXISTING_REPL_ID" ]; then
  echo "Deleting existing replication ID: $EXISTING_REPL_ID"
  influx replication delete --id "$EXISTING_REPL_ID" \
    --host "$INFLUX_HOST" --token "$INFLUX_TOKEN" 2>/dev/null || true
fi

# Create replication
echo "Creating replication stream..."
influx replication create \
  --name "edge-to-ground" \
  --remote-id "$REMOTE_ID" \
  --local-bucket-id "$BUCKET_ID" \
  --remote-bucket "$INFLUX_BUCKET" \
  --host "$INFLUX_HOST" \
  --token "$INFLUX_TOKEN" \
  --org "$INFLUX_ORG"

echo ""
echo "========================================="
echo "Replication setup complete!"
echo "========================================="
echo ""
influx replication list --host $INFLUX_HOST --token $INFLUX_TOKEN --org $INFLUX_ORG
echo ""
