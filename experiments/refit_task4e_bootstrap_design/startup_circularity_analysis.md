# Task 4E: Startup Circularity Analysis

## Scope and conclusion

This is a repository-only planning analysis. No Docker command, HTTP request, database initialization, identity, device, token, secret, or application configuration change was performed.

**Conclusion:** Task 4C has no literal Docker `depends_on` cycle. Its service graph is acyclic. It does have a **genuine configuration-and-provisioning bootstrap circularity** that blocks a secure full-stack start:

```text
Full Task 4C configuration requires real H1/H2/H4 deviceId:secret mappings
        -> those mappings require database-generated device IDs
        -> device IDs require authenticated profile/device provisioning
        -> provisioning requires an isolated ADMIN gateway path
        -> the full Gateway cannot start until the mapping-dependent Ingestion Service can start
        -> full configuration therefore cannot provide the path needed to create its own mappings
```

The proposed resolution is a separately reviewed, provisioning-only isolated stage before the full Task 4C telemetry stage. It is a design recommendation only; it is not implemented or authorized here.

## 1. Exact evidence for the circularity

| Link in the loop | Verified evidence | Dependency class | Finding |
|---|---|---|---|
| Full Compose requires the device-token mapping. | `experiments/refit_task4c_deployment_preparation/docker-compose.refit.yml:137,206` use mandatory `REFIT_IOT_INGESTION_DEVICE_TOKENS` interpolation. | Configuration-time prerequisite | Compose configuration cannot proceed without a nonempty value before any relevant container starts. |
| Ingestion fails closed without a device mapping when authorization is on. | `ingestion-service/src/main/java/com/hometracker/ingestion_service/security/IngestionAuthorizationService.java:67-81` | Application startup prerequisite | With `INGESTION_AUTH_REQUIRED=true`, an empty mapping (and disabled legacy fallback) raises an initialization error. |
| Mapping format needs a real device ID and a unique secret. | `IngestionAuthorizationService.java:149-177` | Authorization/data prerequisite | Entries must be `deviceId:token`; invalid IDs, duplicate IDs, and reused token values are rejected. |
| Device IDs only exist after record persistence. | `device-service/src/main/java/com/hometracker/device_service/entity/Device.java:17-28`; `.../service/DeviceService.java:27-35,67-74` | Database/provisioning prerequisite | IDs are database generated and returned by the supported creation workflow. REFIT labels H1/H2/H4 are not backend IDs. |
| Profile creation needs a secured administrative gateway route. | `api-gateway/src/main/java/com/hometracker/api_gateway/config/SecurityConfig.java:38-47`; `user-service/.../controller/UserController.java:25-30` | OIDC/authorization prerequisite | `POST /api/v1/user` requires `ADMIN`; creation is forwarded through the gateway. |
| Device Service is private and expects gateway/private-service evidence. | `device-service/.../security/OwnershipVerifier.java:42-85`; `DeviceController.java:33-39` | Application authorization prerequisite | A supported provisioning workflow must preserve the gateway authorization boundary; it must not call a service directly as a shortcut. |
| Full Gateway waits for Ingestion Service to be started. | `docker-compose.refit.yml:208-216` | Container-start dependency | Gateway has `depends_on` entries for User, Device, Ingestion, and Usage services. |

## 2. Why this is not merely a missing value

The missing mapping cannot safely be filled with a placeholder, source household number, global token, existing development token, or security-disabled setting:

- H1/H2/H4 device IDs do not exist yet and must be captured from approved creation responses.
- A fresh experiment database also receives Flyway demo seed rows (`user-service/src/main/resources/db/migration/V5__seed_demo_household.sql:1-10` and `V7__seed_security_demo_user.sql:1-4`), so numeric IDs are not predictable.
- The configuration explicitly disables legacy global-token fallback (`docker-compose.refit.yml:138`), and the frozen Task 4C security design must remain enabled.
- API Gateway itself parses a configured mapping but does not make a blank mapping usable for machine telemetry (`api-gateway/.../filter/IotIngestionTokenFilter.java:54-128`). Ingestion Service remains the exact device-ID binding point.

Therefore, this is a real operational cycle: the full composition needs provisioning output before it can supply the secure provisioning route. It is not a Docker-engine deadlock, nor is it an OIDC discovery loop.

## 3. Existing container and readiness graph

### 3.1 Verified Compose relationships

| Service | Compose prerequisite | Type | Readiness limitation |
|---|---|---|---|
| MySQL | None | Persistent-store initialization | Has a MySQL health check (`docker-compose.refit.yml:18-22`). |
| Kafka | None | Persistent-store/broker initialization | No Compose health check; downstream services use only `service_started`. |
| InfluxDB | None | Persistent-store initialization | Has an HTTP health check (`docker-compose.refit.yml:72-76`). |
| User Service | MySQL healthy | Container start after database health | Owns Flyway migrations; no Compose application-health condition. |
| Device Service | MySQL healthy | Container start after database health | Flyway is disabled; it can race the shared-schema migration unless a staged plan waits for User Service completion. |
| Ingestion Service | Kafka started, Device Service started | Container-start dependency | Needs required mapping and gateway proof at application construction; neither dependency is Compose-health-checked. |
| Usage Service | Kafka started, InfluxDB healthy, User Service started, Device Service started | Container-start plus Influx health | User/Device/Kafka are not Compose-health-checked. |
| API Gateway | User, Device, Ingestion, Usage started | Container-start dependency | No Compose application-health condition; isolated issuer/JWK configuration is external to this graph. |

The Compose dependency graph is directed and acyclic. `service_started` means the dependency container has started; it does not prove Spring application readiness, Flyway completion, Kafka readiness, or route availability.

### 3.2 OIDC dependency classification

Task 4C declares no Keycloak service. Gateway requires an externally supplied `KEYCLOAK_ISSUER_URI` and `KEYCLOAK_JWK_SET_URI` (`docker-compose.refit.yml:201-207`). The gateway source is configured as an OAuth2 resource server (`api-gateway/src/main/resources/application.properties:7-11`; `SecurityConfig.java:31-47`).

This is an **external identity readiness/configuration dependency**, not a Compose `depends_on` edge. The repository does not define an explicit startup health probe to an isolated issuer. The explicit JWK-set property means the exact timing of remote key retrieval is framework/runtime behavior that must be observed only during a later approved smoke test. Regardless of that timing, a valid isolated issuer and JWK endpoint must be ready before an `ADMIN` token can support provisioning.

## 4. Additional readiness risks, distinct from the cycle

1. **Shared-schema migration order.** User Service has `spring.flyway.enabled=true`; Device Service has `spring.flyway.enabled=false` (`user-service/src/main/resources/application.properties:9-12`; `device-service/src/main/resources/application.properties:9-11`). Both currently depend only on MySQL health. A safe staged procedure must wait for User Service migration/application health before starting or using Device Service.
2. **Kafka readiness.** Ingestion and Usage Service depend on Kafka `service_started`, not a broker health check (`docker-compose.refit.yml:140-144,166-174`). This is a readiness-risk, not a cycle.
3. **Usage background work.** Usage Service has a scheduled ten-second aggregate routine (`usage-service/src/main/java/com/hometracker/usage_service/service/UsageService.java:78-180`). It queries InfluxDB even when no replay is run. In a genuinely fresh, empty experiment bucket this should find no energy points and therefore no device-energy records, but that is a condition to verify later rather than a result claimed now.
4. **Simulation remains excluded.** Task 4C sets `SIMULATION_ENABLED=false` (`docker-compose.refit.yml:132-138`); both simulator components are conditional on the property (`ingestion-service/.../simulation/ParallelDataSimulator.java:24-27`). No simulator should create events during an approved deployment-only smoke test.
5. **Alert/ML exclusion is not a source deletion.** Alert and ML services are absent from Task 4C. Gateway's retained Alert/Insight routes intentionally target a fail-closed local endpoint (`docker-compose.refit.yml:197-200`), but tests must not call those routes.

## 5. Minimum safe design direction

The least invasive path that preserves the existing source contract is:

1. **Provisioning-only isolated stage:** isolated identity provider, isolated MySQL, API Gateway, User Service, and Device Service; no Ingestion, Usage, Kafka, InfluxDB, Alert, ML, simulator, replay, or event generator.
2. Use a new isolated `ADMIN` identity to create application profiles and exactly one `GENERAL` device per profile through the supported gateway workflow.
3. Record returned IDs in a non-secret ledger and verify the H1/H2/H4 ownership/cardinality mapping.
4. Generate the three device-bound secrets outside the backend through an approved secret-management process; inject the identical mapping into future Gateway and Ingestion instances.
5. **Full telemetry stage:** only after mapping, issuer, secrets, initialization, and state-continuity approvals are complete, start the approved Task 4C services.

The provisioning-only stage must be represented by a future separately reviewed Compose/overlay design. It must be sequentially handed off to the full telemetry stage using the same dedicated experiment-only MySQL state, never a guessed identifier and never an export/import shortcut unless separately approved.

## 6. Remaining unresolved dependencies

- No isolated OIDC issuer/realm/persistent-store design is implemented.
- No provisioning-only isolated composition has been authored or reviewed.
- No approved MySQL state-continuity method exists between provisioning and full telemetry stages.
- No backend device-secret issuance/rotation mechanism exists; this is external operational work.
- No approval exists for persistent-store initialization, service start, profile/device creation, secret issuance, or request execution.

These are execution blockers, so the Task 4E final status remains **NO-GO — BOOTSTRAP BLOCKERS REMAIN**.
