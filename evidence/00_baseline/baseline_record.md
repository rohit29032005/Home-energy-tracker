# Baseline record

**Observed on:** 2026-10-04 (Asia/Kolkata)

## Repository state observed before the upgrade

The repository contains seven Java/Spring services (`api-gateway`, `user-service`, `device-service`, `ingestion-service`, `usage-service`, `alert-service`, and `insight-service`), a React/Vite frontend, an ESP32/Wokwi simulator, Docker Compose definitions, MySQL, Kafka, InfluxDB, Mailpit, and a root dataset named `smart_meter_data.csv`.

The baseline telemetry contract is `{deviceId, energyConsumed, timestamp}`. The ingestion service validates the request and publishes `energy-usage` to Kafka. The usage service consumes that topic and writes InfluxDB points. The alert path is threshold-based: the usage service emits `energy-alerts`, then the alert service persists an alert and requests email delivery through Mailpit. The insight service performs deterministic bill, appliance-ranking, and standby-load calculations. Existing Spring AI/Ollama code is treated as a narrative component, not as anomaly detection.

## Initial verification attempts

| Check | Observed result | Interpretation |
| --- | --- | --- |
| `docker compose ps --all` | Could not connect to `//./pipe/docker_engine`; Docker Desktop Service was `Stopped`. | Live containers, Kafka flow, database connectivity, dashboard, notification, performance, and resilience tests could not be executed at this point. |
| `mvn -B test` with the default Maven repository | Failed before compilation because Maven attempted to create `C:\\.m2\\repository`, which is inaccessible in this sandbox. | Environment-path issue, not a source-code result. |
| `mvn -B -Dmaven.repo.local=<project>\\.maven-cache test` | User-service completed successfully; device-service and ingestion-service reports were regenerated successfully before the command time limit. | A project-local Maven repository is required for reproducible sandbox runs. |
| `npm --version` | Failed because the configured global npm CLI file was missing. | Frontend build was not executable until the local Node/npm installation is repaired or an alternative npm executable is selected. |
| Python ML imports | `pandas`, `scikit-learn`, `joblib`, `fastapi`, and `uvicorn` were not installed in the system Python. | A dedicated project virtual environment is needed before ML training/inference can run. |

## Baseline limitations

This record intentionally does not claim that Docker, frontend, Kafka, databases, Mailpit, Wokwi, or any HTTP endpoint was live on 2026-10-04. Those statements require a later successful runtime execution and are recorded separately when performed.
