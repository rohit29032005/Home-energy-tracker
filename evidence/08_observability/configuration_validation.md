# Observability configuration validation

**Static validation dates:** 2026-10-10 and 2026-10-11 (local environment)

The following static configuration checks completed successfully:

| Item | Validation performed | Result |
|---|---|---|
| Docker Compose (development and production) | `docker compose config --no-interpolate --quiet` with an isolated Docker CLI config | Both parsed successfully; rechecked on 2026-10-11 after gateway/internal token wiring was added to usage, alert, and insight services |
| Prometheus configuration | PyYAML parse of `docker/prometheus/prometheus.yml` | Parsed successfully |
| Grafana datasource and dashboard provider | PyYAML parse of both provisioning files | Parsed successfully |
| Grafana operations dashboard | JSON parse of `docker/grafana/provisioning/dashboards/json/het-overview.json` | Parsed successfully |
| Monitoring persistence | Named Prometheus/Grafana data volumes in development and production Compose files | Declared successfully |

Configured observability components include Spring Boot Actuator/Prometheus exposure, Prometheus scraping configuration, a provisioned Grafana datasource and operations dashboard, persistent development/production monitoring volumes, and alert creation/suppression counters. Production Compose keeps Prometheus on the internal Docker network and binds Grafana to loopback with required deployment-time credentials. The production Nginx configuration no longer proxies public `/actuator/*` requests. The dashboard includes target health, gateway 5xx rate, ML failure/latency, alert decisions, and the isolated REFIT experimental-stream counters.

Historical runtime captures from **2026-10-05** are retained in this directory: they recorded 8/8 Prometheus targets `up` and cumulative alert suppression counters. They do not validate the dashboard or production monitoring declaration added on 2026-10-10. On 2026-10-10, `docker compose ps --all` could not connect to `//./pipe/docker_engine`; an earlier 2026-10-11 session received a permission-denied response from that boundary, and a subsequent elevated 2026-10-11 `docker compose ps` recheck found that `//./pipe/dockerDesktopLinuxEngine` did not exist. The 2026-10-11 Compose parse did not require a running daemon and does not change that limitation. Current dashboard loading, current target health, Grafana credential enforcement, Kafka lag, CPU/memory, and new latency measurements are **NOT YET MEASURED**.
