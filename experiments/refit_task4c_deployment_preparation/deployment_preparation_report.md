# Task 4C — Isolated REFIT Docker Deployment Preparation

**Date:** 2026-10-14  
**Scope:** Static configuration and repository inspection only. No Docker lifecycle command, image build/pull, database initialization, profile/device/token creation, HTTP request, Kafka event, replay, model operation, or source-code modification was performed.

## Decision

**NO-GO — BLOCKERS REMAIN.**

The supplied Compose file is a reviewable, fail-closed deployment preparation artifact. It is not approved to start. It deliberately requires an isolated OIDC issuer/JWK endpoint and future H1/H2/H4 device-token mapping, neither of which exists at this stage.

Static Compose parsing and resolved-configuration checks passed with temporary non-secret validation strings only. Details are recorded in [static_validation_report.md](static_validation_report.md); this does not establish runtime isolation or authorization readiness.

## Prepared configuration

`docker-compose.refit.yml` contains exactly the approved eight services:

1. `mysql`
2. `kafka`
3. `influxdb`
4. `user-service`
5. `device-service`
6. `ingestion-service`
7. `usage-service`
8. `api-gateway`

It omits `ml-inference-service`, `alert-service`, `insight-service`, frontend, simulator/replay services, Keycloak, Mailpit, monitoring, and event generators. It uses no `container_name` entries; the Compose project name and isolated network/volume names provide a separate namespace.

| Control | Prepared design | Evidence |
|---|---|---|
| Compose scope | Eight approved services only | `docker-compose.refit.yml` |
| Container names | Omitted, so Docker Compose applies the `refit-task4c` project namespace | `docker-compose.refit.yml` |
| Network | Dedicated bridge network `refit-task4c-network` | `docker-compose.refit.yml` |
| Stateful storage | `refit-task4c-mysql-data`, `refit-task4c-kafka-data`, and `refit-task4c-influx-data` only | `docker-compose.refit.yml` |
| Database/resource names | `refit_experiment`, `refit_experiment`, and `refit_experiment_usage` | `docker-compose.refit.yml`, `.env.example` |
| Host exposure | Loopback-only gateway mapping `127.0.0.1:18080:8080`; no MySQL, Kafka, InfluxDB, or private-service host port | `docker-compose.refit.yml` |
| Security posture | `SECURITY_ENABLED=true`, `INGESTION_AUTH_REQUIRED=true`, and legacy global device token disabled | `docker-compose.refit.yml` |
| Simulator/replay | `SIMULATION_ENABLED=false`; no replay container or event generator | `docker-compose.refit.yml` |
| ML/Alert boundary | No ML or Alert service is defined; a separate Kafka volume and network prevent broker sharing | `docker-compose.refit.yml`; `ml-service/app/kafka_worker.py:102-170` |

## Reused and independently authored material

| Category | Reused without modification | Independently authored for Task 4C |
|---|---|---|
| Application images | Existing service Dockerfiles for User, Device, Ingestion, Usage, and Gateway | New build contexts relative to this Task 4C directory |
| Infrastructure image references | Existing MySQL `8.3.0`, InfluxDB `2.7`, and Kafka image reference | Dedicated KRaft cluster identifier, network, volume names, database/org/bucket names, and port binding |
| Service configuration | Existing environment-property contracts and internal Docker DNS patterns | REFIT-only variable names, fail-closed OIDC placeholders, disabled simulator, and omitted dependencies |
| Original deployment files | `docker-compose.yml` and `docker-compose.prod.yml` | `experiments/refit_task4c_deployment_preparation/docker-compose.refit.yml` only |

The Kafka image remains `apache/kafka:latest` because that is the repository's existing reference. It is syntactically valid for static review, but its mutable tag is a reproducibility issue that must be pinned to an approved digest/tag before any runtime deployment.

## Service communication boundary

All included services use Docker DNS only on `refit-task4c-network`: `mysql`, `kafka`, `influxdb`, `user-service`, `device-service`, `ingestion-service`, and `usage-service`. No address refers to the existing development or production network.

The API gateway has source-level routes for Alert and Insight (`api-gateway/src/main/resources/application.properties:37-43`). They have no required Compose dependency. The Task 4C configuration assigns both routes to `127.0.0.1:9` inside the gateway container, making them intentionally unavailable rather than allowing an accidental connection to a shared service.

## H1/H2/H4 household model

The existing supported model can represent the future household separation without a schema or authorization change:

| REFIT household | Future application profile | Future device | Existing support |
|---:|---|---|---|
| H1 | Separate profile | One `GENERAL` aggregate meter | `DeviceType.GENERAL`; `DeviceDto` includes `userId` |
| H2 | Separate profile | One `GENERAL` aggregate meter | Same workflow, distinct database-generated IDs |
| H4 | Separate profile | One `GENERAL` aggregate meter | Same workflow, distinct database-generated IDs |

Evidence: `user-service/src/main/java/com/hometracker/user_service/service/UserService.java:21-32`, `device-service/src/main/java/com/hometracker/device_service/service/DeviceService.java:27-35`, `device-service/src/main/java/com/hometracker/device_service/model/DeviceType.java:3-15`, and `user-service/src/main/resources/db/migration/V2__device_table.sql`.

The source house number is not a backend identifier. New IDs must be returned by the approved profile/device creation workflow. The fresh database's existing migrations seed demonstration rows, so generated IDs cannot be predicted from REFIT household numbers.

## Preserved energy contract

The verified Task 2 mapping is retained without implementation change:

```text
derived_interval_energy_kwh -> energyConsumed
```

The future Compose file neither replays a record nor performs a unit conversion. The ingestion DTO and service retain the existing `energyConsumed` field path (`ingestion-service/src/main/java/com/hometracker/ingestion_service/dto/EnergyUsageDto.java:11-18`; `.../service/IngestionService.java:24-35`).

## Critical blockers

1. **Independent OIDC/Keycloak is absent.** The Gateway remains secured and needs an ADMIN JWT to create application profiles. The eight approved services do not include Keycloak. Existing development defaults must not be reused. See `api-gateway/src/main/resources/application.properties:7-11` and `api-gateway/src/main/java/com/hometracker/api_gateway/config/SecurityConfig.java:39-46`.
2. **No experiment device IDs or token mappings exist.** Ingestion fails closed when authorization is enabled but the device-token map or gateway proof is absent. See `ingestion-service/src/main/java/com/hometracker/ingestion_service/security/IngestionAuthorizationService.java:67-81,149-177`.
3. **No runtime initialization approval exists.** A future start would initialize a new MySQL and InfluxDB state and let User Service run Flyway migrations. Task 4C deliberately did not perform that action.

All unresolved items and required evidence are recorded in [open_blockers.md](open_blockers.md).
