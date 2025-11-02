# Ground Station Monitoring Stack

Monitoring stack pro Ground Station s VictoriaMetrics a Grafanou.

## Rychlý start

```bash
./start.sh
```

## Přístup

- **Grafana**: http://localhost:3000 (admin/admin123)
- **VictoriaMetrics**: http://localhost:8428/vmui
- **InfluxDB v1 write**: http://localhost:8428/write
- **InfluxDB v2 write**: http://localhost:8089/api/v2/write

## Použití

### Zápis dat (InfluxDB Line Protocol)

```bash
curl -d 'temperature,sensor=ground_station value=23.5' http://localhost:8428/write
```

## Správa

```bash
docker compose logs -f              # Zobrazit logy
docker compose stop                 # Zastavit
docker compose start                # Spustit
docker compose restart              # Restart
docker compose down                 # Vypnout a smazat containery
docker compose down -v              # Smazat včetně dat
```

## Odkazy

- [VictoriaMetrics docs](https://docs.victoriametrics.com/)
- [Grafana docs](https://grafana.com/docs/)
