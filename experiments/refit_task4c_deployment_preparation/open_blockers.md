# Task 4C — Open Blockers

## Decision

**NO-GO — BLOCKERS REMAIN.** The configuration may be reviewed statically but must not be started until the critical items below are resolved through explicit approval.

| ID | Severity | Blocker | Evidence | Required resolution |
|---|---|---|---|---|
| C1 | Critical | No isolated OIDC/Keycloak issuer is supplied within the eight-service scope. | Gateway requires secure JWT configuration (`api-gateway/src/main/resources/application.properties:7-11`) and `ADMIN` for profile creation (`SecurityConfig.java:39-46`). | Approve either a separate isolated Keycloak service/realm or a separately operated isolated OIDC provider with verified issuer/JWK URLs. Do not use the existing dev Keycloak. |
| C2 | Critical | H1/H2/H4 application device IDs and unique device-bound tokens do not exist. | Ingestion parses exact mappings and fails closed when auth is enabled without them (`IngestionAuthorizationService.java:67-81,149-177`). | After deployment/provisioning approval, create three isolated profiles/devices through the existing secure workflow; record returned IDs; inject three unique secret mappings into isolated Gateway and Ingestion only. |
| C3 | Critical for runtime start | Runtime initialization is not authorized. | New MySQL/Influx resources would initialize on first start; User Service enables Flyway (`user-service/src/main/resources/application.properties:9-12`). | Explicitly approve isolated runtime start and initialization only after C1/C2 are resolved. |
| C4 | High | No runtime readiness/isolation evidence exists. | Static `depends_on` covers MySQL/Influx health, while Kafka and app dependencies are only `service_started`. | Conduct a separate approved deployment-only smoke-test review with no data events. |
| C5 | High | Kafka image is a mutable `latest` reference inherited from current configuration. | `docker-compose.refit.yml` uses `apache/kafka:latest`; current Compose does likewise. | Pin an approved Kafka image tag/digest before execution and record it in the experiment manifest. |
| C6 | Medium | Gateway source retains Alert/Insight route definitions, though those services are excluded. | `api-gateway/src/main/resources/application.properties:37-43`. | Keep Task 4C fail-closed local route targets; acknowledge those endpoints are unavailable. A source change would require separate approval and is not needed for initial scope. |
| C7 | Medium | Usage Service can publish `energy-alerts` for enabled profiles even without Alert Service. | `usage-service/src/main/java/com/hometracker/usage_service/service/UsageService.java:78-180`. | Future experiment profiles must set `alerting=false`; do not send telemetry until this is verified. |
| C8 | Medium | Static validation does not establish cleanup semantics or idempotency for a future replay. | Task 3/4 reports; ingestion has no verified idempotency key. | Retain the frozen conservative replay protocol and seek separate approval before first ingestion. |
| C9 | Low | Port 18080 was free only at the static inspection time. | Read-only host snapshot; port ownership can change. | Recheck immediately before any approved start, and choose a new loopback port if occupied. |

## Explicitly rejected shortcuts

- Reusing the existing Keycloak issuer/JWK endpoint.
- Setting `SECURITY_ENABLED=false` or `INGESTION_AUTH_REQUIRED=false`.
- Reusing the existing device-1/Wokwi token or inferring backend IDs from REFIT house numbers.
- Pointing the experiment at existing Kafka, MySQL, InfluxDB, Docker volumes, or networks.
- Adding ML, Alert, replay, simulator, or event-generator services to this initial Compose file.
