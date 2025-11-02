#!/bin/bash

# Ground Station Monitoring Stack - Startup Script
# VictoriaMetrics + Grafana

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "Starting Ground Station Monitoring Stack..."
echo ""

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker není spuštěný. Prosím spusť Docker a zkus to znovu."
    exit 1
fi

# Check if docker-compose is available
if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null 2>&1; then
    echo "❌ Docker Compose není nainstalovaný."
    exit 1
fi

# Determine which docker compose command to use
if docker compose version &> /dev/null 2>&1; then
    COMPOSE_CMD="docker compose"
else
    COMPOSE_CMD="docker-compose"
fi

# Create necessary directories
echo "Vytvářím potřebné adresáře..."
mkdir -p grafana/provisioning/datasources

# Ensure datasource config exists
if [ ! -f grafana/provisioning/datasources/victoriametrics.yml ]; then
    echo "Chybí konfigurace datasource, vytvářím..."
    cat > grafana/provisioning/datasources/victoriametrics.yml <<EOF
apiVersion: 1

datasources:
  - name: VictoriaMetrics
    type: prometheus
    access: proxy
    url: http://victoriametrics:8428
    isDefault: true
    editable: true
    jsonData:
      timeInterval: 30s
EOF
fi

echo "Stahuji Docker images..."
$COMPOSE_CMD pull

echo ""
echo "Spouštím containery..."
$COMPOSE_CMD up -d

echo ""
echo "Čekám na inicializaci služeb..."
sleep 10

# Wait for services to be healthy
echo "Kontroluji stav služeb..."
timeout=60
elapsed=0
while [ $elapsed -lt $timeout ]; do
    if docker ps | grep -q victoriametrics && docker ps | grep -q grafana; then
        if curl -s http://localhost:8428/health > /dev/null 2>&1 && \
           curl -s http://localhost:3000/api/health > /dev/null 2>&1; then
            break
        fi
    fi
    sleep 2
    elapsed=$((elapsed + 2))
done

# Check if services are running
if docker ps | grep -q victoriametrics && docker ps | grep -q grafana; then
    echo ""
    echo "✅ Vše běží!"
    echo ""
    echo "Přístupové údaje:"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "     Grafana:          http://localhost:3000"
    echo "     Username:         admin"
    echo "     Password:         admin123"
    echo ""
    echo "     VictoriaMetrics:  http://localhost:8428"
    echo "     UI:               http://localhost:8428/vmui"
    echo "     API Endpoint:     http://localhost:8428/api/v1"
    echo ""
    echo "     Write Endpoints:"
    echo "     Prometheus:       http://localhost:8428/api/v1/write"
    echo "     InfluxDB v1:      http://localhost:8428/write"
    echo "     InfluxDB v2:      http://localhost:8089/api/v2/write"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "   Užitečné příkazy:"
    echo "  Zobrazit logy:        $COMPOSE_CMD logs -f"
    echo "  Zastavit:             $COMPOSE_CMD stop"
    echo "  Spustit znovu:        $COMPOSE_CMD start"
    echo "  Restart:              $COMPOSE_CMD restart"
    echo "  Vypnout a smazat:     $COMPOSE_CMD down"
    echo "  Smazat vč. dat:       $COMPOSE_CMD down -v"
    echo ""
    echo "Pro více informací viz README.md"
    echo ""
else
    echo ""
    echo "Některé služby se možná nespustily správně."
    echo "Zobraz logy pomocí: $COMPOSE_CMD logs"
    exit 1
fi
