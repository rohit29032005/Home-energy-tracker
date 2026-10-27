# Step 1 — Existing Stack Recovery and Health Verification

## Scope

This record covers the approved staged restart of the existing Home Energy Tracker containers and read-only health checks. No REFIT replay, profile/device provisioning, telemetry submission, model retraining, or database migration was intentionally performed.

## Recovery protection

Before startup, an access-restricted backup was created outside the Git workspace. The backup contains:

- A MySQL application-database logical dump, created with `mysqldump --single-transaction`, size 58,324 bytes, SHA-256 `9EC7ACEBB53DD11905F6F6044EF7261EF24593A3E54F8D20BF2494150DF9761D`.
- An InfluxDB data/configuration copy: 37 data files (67,301,335 bytes) and one configuration file (440 bytes).
- A Keycloak container-filesystem export, SHA-256 `97345A43296D973C8CC72EEEE99AF23FFA32BCE8696D62B13576863E85521539`.
- Protected current Compose/runtime configuration copies and a 42-file SHA-256 manifest.

The stopped Kafka data directory copied successfully but contained zero files. No isolated restore test was run; such a test requires separate approval.

## Startup evidence

- Kafka started first and logged transition from `STARTING` to `STARTED`; measured memory was about 375 MiB after start.
- InfluxDB and Mailpit reported Docker health `healthy`; Keycloak was running.
- `user-service` validated seven Flyway migrations. The schema was already at version 7 and Flyway reported that no migration was necessary.
- Device, ML inference, usage, alert, insight, ingestion, API gateway, and frontend containers were started without recreation or rebuild.
- At the final core-stack check, all 15 required containers were running. Prometheus and Grafana were deliberately left stopped because total core-container memory was approximately 2.9 GiB of the 3.696 GiB available Docker memory, and Kafka had a prior OOM event.

## Final read-only health sweep

All checks were `GET /actuator/health` requests executed from the existing ML container over the Docker network. They did not submit telemetry or use credentials.

| Service | HTTP status | Response time (s) |
|---|---:|---:|
| user-service | 200 | 0.201 |
| device-service | 200 | 0.203 |
| ingestion-service | 200 | 0.178 |
| usage-service | 200 | 0.124 |
| alert-service | 200 | 0.162 |
| insight-service | 200 | 0.162 |
| api-gateway | 200 | 0.278 |

Host-visible checks also returned HTTP 200 for the frontend, InfluxDB, Keycloak OpenID configuration, Mailpit, Kafka UI, and API gateway. The ML port is intentionally not host-published; its internal `/health` endpoint returned HTTP 200.

## Known limitation

The alert service's first short startup-period probe timed out; a subsequent 25-second probe and the final sweep returned HTTP 200. Historical metric-endpoint content-type warnings remain observable in earlier logs and are not treated as a current service-start failure.

## Step status

**COMPLETE — core existing stack started and health-verified.** This does not authorize REFIT replay, create experiment identities, or submit data.
