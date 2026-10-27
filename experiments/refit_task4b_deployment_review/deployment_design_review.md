# Task 4B — Isolated REFIT Deployment Design Review

**Status:** Planning and static review complete. No deployment action is authorized.  
**Review date:** 2026-10-13  
**Inspection method:** Repository files and existing Task 2–4A evidence only. No Docker command, HTTP request, Kafka message, device/token creation, container action, or replay was performed.

## Decision

**GO FOR DEPLOYMENT PLANNING ONLY.**

This is not approval to create a Compose deployment, profiles, devices, credentials, or a replay. The design can be made genuinely isolated, but only with a new deployment specification and separate stateful resources. The current shared stack remains **NO-GO** for REFIT replay.

## Verified current implementation facts

| Subject | Verified fact | Evidence |
|---|---|---|
| Household/device relationship | A device record stores `name`, `type`, `location`, and `userId`; device creation is available at `POST /api/v1/device`. | `device-service/src/main/java/com/hometracker/device_service/dto/DeviceDto.java`, `.../service/DeviceService.java:27-35`, `.../controller/DeviceController.java:33-38` |
| Profile provisioning | Application profiles are created through the protected user workflow; the existing project documentation states that this creates an application record rather than a Keycloak login. | `user-service/.../controller/UserController.java:25-30`; `docs/11-professor-live-demo-script.md:184-219` |
| Device credentials | There is no token entity, table, issue endpoint, rotation endpoint, or automatic pairing flow. Tokens are read from `IOT_INGESTION_DEVICE_TOKENS` at service startup. | `ingestion-service/.../IngestionAuthorizationService.java:42-81, 133-177`; `ingestion-service/src/main/resources/application.properties:16` |
| Device-token authorization | Ingestion retrieves the expected token by payload `deviceId`; the gateway accepts a configured machine token but the downstream ingestion service performs the exact binding. | `ingestion-service/.../IngestionAuthorizationService.java:84-104, 133-146`; `api-gateway/.../IotIngestionTokenFilter.java:61-109` |
| Ingestion event path | Ingestion publishes an accepted payload to Kafka topic `energy-usage`. | `ingestion-service/.../IngestionService.java:24-35` |
| Usage persistence | Usage consumes `energy-usage` in group `usage-service` and writes `energy_usage` points to InfluxDB. | `usage-service/.../UsageService.java:61-76` |
| Legacy ML path | The legacy ML worker consumes `energy-usage` with group `ml-inference-service` and publishes `anomaly-results`. | `ml-service/app/kafka_worker.py:102-113, 161-170` |
| Alert path | Alert Service consumes both `energy-alerts` and `anomaly-results`. | `alert-service/.../AlertService.java:47-72` |
| Current Compose collision risk | The development Compose file uses fixed container names, fixed host ports, and shared named volumes. | `docker-compose.yml:4-352` |
| Production network | The production Compose file uses an explicit `energy-net` plus fixed `*-prod` container names and named volumes. | `docker-compose.prod.yml:7-328` |

## Required deployment topology

The future REFIT experiment is a **parallel deployment**, not an addition to the running shared stack.

```text
REFIT replay tool (not created in Task 4B)
       |
       v
isolated API Gateway + isolated Ingestion Service
       |
       v
isolated Kafka broker / isolated energy-usage topic
       |
       +--> isolated Usage Service --> isolated InfluxDB
       |
       +--> [excluded during initial validation] ML / Alert path

isolated User Service + isolated Device Service + isolated MySQL
```

The experiment configuration must create three separate application household profiles—one each for REFIT Houses 1, 2, and 4—with one `GENERAL` logical aggregate-meter device under each profile. Three profiles are necessary because existing usage and threshold calculations group devices by `userId` (`usage-service/.../UsageService.java:112-180, 194-278`). One profile with three devices would merge independent households in dashboard and alert calculations.

## What must be newly designed later

No file is created by Task 4B. A future, explicitly approved implementation needs a deployment-only Compose specification, for example `docker-compose.refit-experiment.yml`, with:

1. No collision with `docker-compose.yml` fixed container names; omit `container_name` where practical or use an unambiguous `refit-exp-*` prefix.
2. Its own Docker network, not the current default development network or production `energy-net`.
3. Separate MySQL, Kafka, InfluxDB, Prometheus, and Grafana volumes, all named with a REFIT experiment prefix.
4. Separate and non-conflicting host-port bindings. The preferred initial design exposes only the API gateway and any administrator UI required for provisioning; MySQL, Kafka, InfluxDB, and service ports remain internal.
5. A separate Keycloak instance/realm configuration if JWT/UI administration is used. The development gateway default issuer refers to `localhost:8180`, so it cannot be copied unchanged to an isolated host-port deployment. Evidence: `docker-compose.yml:287-288`.
6. A separate Mailpit instance or no exposed mail service. Experiment profile alerting must be `false`.
7. A separate untracked runtime secret source; tracked examples contain placeholders only.

`docker compose -p refit-experiment` by itself is insufficient: fixed container names and explicitly named volumes in the present Compose files can still collide.

## Current service communication and storage

| Layer | Current verified behavior | Required experiment isolation control |
|---|---|---|
| API gateway | Routes public API traffic to internal services and validates JWT/machine-token telemetry. | Use an isolated gateway connected only to the REFIT network and its isolated Keycloak/JWK endpoint. |
| Device/User | Device records use MySQL and an ownership model. | Create the three new profiles/devices only in isolated MySQL; never use existing profile/device IDs. |
| Ingestion | Publishes to literal topic `energy-usage`. | Use a separate broker so the identical topic name remains isolated by broker boundary. |
| Usage | Consumes `energy-usage` and persists energy points in configured Influx bucket. | Point only at isolated Kafka and isolated Influx credentials/bucket. |
| ML | Legacy worker consumes all events from its broker's `energy-usage` topic. | Do not include the legacy ML service during deployment validation or any initial replay validation. |
| Alert | Consumes threshold and ML topics and stores alerts in MySQL. | Exclude during initial validation; later use only isolated alert/MySQL/Mailpit if explicitly approved. |
| Monitoring | Prometheus statically scrapes Docker service DNS names; Grafana reads Prometheus. | Either omit monitoring initially or deploy its own isolated Prometheus/Grafana, never sharing metrics storage. Evidence: `docker/prometheus/prometheus.yml`. |

## Cross-environment dependency review

### Verified manageable dependencies

- Internal service URLs in Compose use Docker DNS names such as `kafka`, `influxdb`, `device-service`, and `user-service`. A dedicated network with only isolated services will resolve those names locally. Evidence: `docker-compose.yml:151-160, 211-217, 237-244, 278-288`.
- The application uses environment variables for Kafka, MySQL, InfluxDB, Keycloak, and token configuration. A separate environment file can direct a new deployment without backend source changes. Evidence: `docker-compose.yml`, `docker-compose.prod.yml`, `.env.example`.

### Verified risks requiring explicit controls

- The development gateway issuer default is host-addressed (`localhost:8180`); a copied value could validate against the wrong Keycloak instance. Override both issuer and JWK configuration for the isolated identity provider.
- The Wokwi example uses a host-local gateway address. It must not be reused for the REFIT replay path; the future replay configuration must target the approved isolated gateway endpoint. Evidence: `iot-simulator/include/config.h.example`.
- The existing ML legacy worker automatically consumes `energy-usage` when `KAFKA_ENABLED=true`. It must be excluded from the initial isolated deployment. Evidence: `docker-compose.yml:183`, `ml-service/app/main.py:267-270`.
- The current Compose startup policy has health checks for MySQL and InfluxDB but primarily uses `service_started` for other services. The future design needs explicit health/readiness gates before any later data activity. Evidence: `docker-compose.yml:13-17, 73-85, 124-126, 169-172, 220-224`.

## Future profile/device credential plan

After deployment approval, the isolated database must receive the following records through the existing administrator workflow:

| REFIT household | Future application profile | Future device | Type | Alerting |
|---:|---|---|---|---|
| 1 | `REFIT Experiment — House 1` | `REFIT H1 Aggregate Meter` | `GENERAL` | `false` |
| 2 | `REFIT Experiment — House 2` | `REFIT H2 Aggregate Meter` | `GENERAL` | `false` |
| 4 | `REFIT Experiment — House 4` | `REFIT H4 Aggregate Meter` | `GENERAL` | `false` |

Returned profile/device IDs must be captured in a non-secret ledger. Three unique, high-entropy device credentials must then be injected only into the isolated gateway and ingestion service using the structure:

```text
IOT_INGESTION_DEVICE_TOKENS=<H1_DEVICE_ID>:<H1_TOKEN>,<H2_DEVICE_ID>:<H2_TOKEN>,<H4_DEVICE_ID>:<H4_TOKEN>
```

This is a design representation, not a value to be copied into a tracked file. The current shared device-1 mapping must remain untouched.

## Data/event semantics retained for a future replay

| Requirement | Status |
|---|---|
| Preserve REFIT household identity | Planned through one profile/device mapping per source house plus a non-secret local ledger. |
| Preserve original time and source provenance | Required in the future adapter/replay ledger: original Unix time, original timestamp text, source file, source row, interval seconds, and data-quality flags. |
| Payload timestamp | **Unresolved deployment-stage decision:** the public ingestion DTO provides one `timestamp`; Task 3's frozen plan is to preserve original source time outside the payload and use a documented replay-time timestamp for live-like queries. This must be retained in the future replay design. |
| Energy unit | Verified: `derived_interval_energy_kwh` maps directly to `energyConsumed`. No second conversion or raw-Watt substitution is permitted. |
| Chronological ordering | Required of the future replay engine; no engine is created by Task 4B. |
| Idempotency | Not verified. No idempotency key is present in `EnergyUsageDto` or `IngestionService`; ambiguous network outcomes must remain non-retryable until a receipt/reconciliation design is approved. |

## Initial ML-boundary recommendation

For deployment validation, omit `ml-inference-service` and `alert-service` from the isolated service set and send **no events**. This is the minimum safe option because it verifies environment boundaries without loading or invoking any ML consumer.

The repository contains a separate, disabled controlled-REFIT worker using distinct topics (`refit-controlled-replay` and `refit-controlled-anomaly-results`), but it accepts a different experimental payload schema and uses a separate controlled artifact. It is not a substitute for the current ingestion path without a later protocol decision. Evidence: `ml-service/app/refit_kafka_worker.py:1-231`, `ml-service/app/main.py:34-41, 274-283`, `docker-compose.yml:194-198`.

## Unresolved items / blockers

See [open_blockers.md](open_blockers.md) for the required pre-implementation decisions. The main blockers are the absence of the isolated Compose specification, unallocated host ports, no application token-issuance lifecycle, no application-scoped Influx/Kafka cleanup path, and the single-timestamp/no-idempotency ingestion contract.

## Stop condition

Task 4B ends with this review. No deployment, credentials, device records, messages, model operation, or replay action has occurred.
