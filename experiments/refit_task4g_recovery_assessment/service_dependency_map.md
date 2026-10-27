# Task 4G: Service Dependency Map and Proposed Recovery Order

## Status notation

- **Verified** — confirmed by existing Compose/source or Docker metadata.
- **Recommendation** — a future approval-gated recovery sequence, not an action performed here.
- `service_started` means Docker container start ordering only; it is not application readiness.

## 1. Verified existing dependency map

| Service | Current state | Compose dependency | Health/readiness evidence declared | Restart policy |
|---|---|---|---|---|
| MySQL | Running, healthy | None | Docker MySQL health check | `always` |
| Kafka | Exited/OOM-killed | None | No Compose health check | `no` |
| InfluxDB | Exited | None | Docker HTTP health check | `no` |
| Mailpit | Exited | None | No Compose health check | `no` |
| Keycloak | Exited | None | No Compose health check | `no` |
| Kafka UI | Running/degraded | Kafka `service_started` | No Compose health check | `unless-stopped` |
| User Service | Exited | MySQL `service_healthy` | Actuator source exists; no Compose health check | `no` |
| Device Service | Exited | MySQL `service_healthy` | Actuator source exists; no Compose health check | `no` |
| Ingestion Service | Exited | Kafka + Device `service_started` | Actuator source exists; no Compose health check | `no` |
| ML inference | Exited | Kafka `service_started` | No Compose health check | `no` |
| Usage Service | Exited | Kafka `service_started`, InfluxDB healthy, User + Device `service_started` | Actuator source exists; no Compose health check | `no` |
| Alert Service | Exited | Kafka `service_started`, MySQL healthy, Mailpit `service_started` | No Compose health check | `no` |
| Insight Service | Exited | Usage Service `service_started` | No Compose health check | `no` |
| API Gateway | Exited | User, Device, Ingestion, Usage, Alert, Insight, Keycloak `service_started` | Actuator source exists; no Compose health check | `no` |
| Frontend | Exited | API Gateway `service_started` | No Compose health check | `no` |
| Prometheus | Exited | API Gateway `service_started` | No Compose health check | `no` |
| Grafana | Exited | Prometheus `service_started` | No Compose health check | `no` |

Evidence: `docker-compose.yml` service blocks and `depends_on` relationships; Task 4F/Task 4G Docker metadata. The User Service owns Flyway migrations (`user-service/src/main/resources/application.properties:9-12`); Device Service has Flyway disabled (`device-service/src/main/resources/application.properties:9-11`).

## 2. Dependency graph

```text
MySQL [healthy] --> User Service [Flyway owner] --> Device Service
                                 |                    |
                                 +--------------------+

Kafka --> Kafka UI
Kafka --> Ingestion Service <----- Device Service
Kafka --> ML inference
Kafka --> Usage Service <--------- InfluxDB [healthy], User Service, Device Service
Kafka --> Alert Service <--------- MySQL [healthy], Mailpit

Usage Service --> Insight Service

Keycloak + User + Device + Ingestion + Usage + Alert + Insight
                    --> API Gateway --> Frontend, Prometheus --> Grafana
```

The graph is a startup-order declaration, not proof that dependencies are ready or that starting them is harmless.

## 3. Recommended approval-gated recovery order

### Gate R0 — preserve and preflight

Before any lifecycle command, capture non-secret resource identities, confirm no destructive cleanup is planned, obtain a persistent-data backup/rollback plan, and verify that no REFIT resource will be involved.

### Gate R1 — Kafka diagnosis and broker-only recovery

Resolve Kafka resource/capacity questions first. After separate approval, start/observe only the existing Kafka broker container, not a Compose-wide operation. Require broker readiness evidence and a plan for existing topics/consumer offsets before any dependent service starts.

### Gate R2 — independent infrastructure assessment

After Kafka is stable, separately assess existing InfluxDB, Keycloak, and Mailpit. Do not assume their current persistent/initialization state is a no-op. Keep Gateway and consumers stopped at this stage.

### Gate R3 — database-backed core services

MySQL is already running. Before starting User Service, approve Flyway risk handling and backup/rollback evidence because startup may validate/apply pending migrations. Wait for User Service migration/application readiness before Device Service. This order is stricter than the Compose parallel startup declaration and prevents use of an incompletely migrated shared schema.

### Gate R4 — event-processing services

Before each service start, approve its side-effect controls:

- **Ingestion:** verify effective simulation is disabled without exposing configuration values. Simulator components activate only when `simulation.enabled=true` (`ingestion-service/.../simulation/ContinuousDataSimulator.java:22`; `ParallelDataSimulator.java:26`).
- **Usage:** assess retained Kafka records and Influx data. It consumes `energy-usage`, writes Influx points, and runs a ten-second scheduled aggregation (`usage-service/.../UsageService.java:61-180`).
- **Alert:** assess queued `energy-alerts`/`anomaly-results` and mail behavior before it can consume/persist/notify.
- **ML:** defer until Kafka/core stability and explicit review; its legacy worker may consume `energy-usage` and publish `anomaly-results` when Kafka is enabled.
- **Insight:** start only after Usage Service behavior is controlled.

### Gate R5 — public path and observation layer

Only after all mandatory Gateway dependencies are application-ready, evaluate Keycloak/Gateway, then frontend and monitoring in the source-declared order. Endpoint testing requires its own approval because Task 4G made no HTTP calls.

## 4. Recovery-order constraints

- Do not use `docker compose up` as a shortcut; it can reconcile/create/pull resources and is outside the read-only assessment.
- Do not use `docker start` until a future gate explicitly authorizes exact named-container action.
- Do not start a consumer merely because Compose reports a producer/broker `service_started`.
- Do not start User Service without a plan for Flyway migration effects on the retained MySQL database.
- Do not start Kafka-dependent consumers until Kafka stability and existing-record side effects have been assessed.
- Do not include or touch REFIT Task 4C resources at any recovery gate.
