# Task 4E: Bootstrap Dependency Graph

## Legend

- `-->` required future dependency or ordered handoff
- `[health]` explicit Compose health condition
- `[started]` Compose container-start condition only; not application readiness
- `(external)` separate isolated component not present in Task 4C
- `[approval]` a human authorization gate, not a technical dependency

## 1. Current Task 4C full-composition graph

```text
                       (isolated OIDC issuer) [external]
                                  |
                                  | issuer/JWK configuration + ADMIN token
                                  v
MySQL [health] --> User Service [started] --+
                  (Flyway owner)             |
                                               +--> API Gateway [started] --> supported profile/device routes
MySQL [health] --> Device Service [started] -+          ^
                                                    requires Ingestion + Usage to be started

Kafka [started] ---> Ingestion Service [started] -------+
                      |                                  |
                      | requires deviceId:secret map     |
                      +----------------------------------+

Kafka [started] --> Usage Service [started] ------------+
InfluxDB [health] -+                                    |
User Service [started] ---------------------------------+
Device Service [started] -------------------------------+

Device IDs from supported Gateway provisioning
                 |
                 v
deviceId:secret map ----------------------> Ingestion Service + API Gateway configuration
```

### Interpretation

The Compose arrows above are acyclic. The operational loop crosses configuration and provisioning boundaries:

```text
device map required for full Gateway/Ingestion startup
       --> secured Gateway route needed to create devices
       --> returned device IDs needed to construct device map
       --> device map required for full Gateway/Ingestion startup
```

This loop cannot be resolved by changing `depends_on` order alone.

## 2. Planned staged graph that removes the operational loop

```text
G0 [approval: static design and secret-injection method]
 |
 v
G1 [approval: initialize isolated identity store + isolated MySQL]
 |
 +--> isolated OIDC provider [ready] (external/new reviewed component)
 |
 +--> isolated MySQL [healthy]
          |
          v
      User Service [healthy; Flyway complete]
          |
          v
      Device Service [healthy]
          |
          +----> provisioning-only API Gateway [OIDC-ready]
                                      |
                                      v
                              isolated ADMIN workflow
                                      |
                                      v
                        three profiles + three GENERAL devices
                                      |
                                      v
                         returned H1/H2/H4 profile/device ID ledger
                                      |
                                      v
G4 [approval: external per-device secret generation/injection]
                                      |
                                      v
                   verified three-entry map for Gateway + Ingestion
                                      |
                                      v
G5 [approval: full Task 4C telemetry stage]
                                      |
        +-----------------------------+----------------------------+
        v                             v                            v
    Kafka [ready]                InfluxDB [healthy]       same isolated MySQL state
        |                             |                            |
        +--> Ingestion [healthy]      +--> Usage [healthy]          |
                     \                /                              |
                      +--> full API Gateway [healthy] <--------------+
                                      |
                                      v
G6 [approval: no-event deployment-only smoke test]
```

## 3. Why User Service precedes Device Service in the planned sequence

Task 4C currently permits both services once MySQL is healthy. However, User Service owns Flyway migrations (`user-service/src/main/resources/application.properties:9-12`), whereas Device Service has Flyway disabled (`device-service/src/main/resources/application.properties:9-11`). The safe future bootstrap must use this stricter application-level order:

```text
MySQL healthy --> User Service application healthy + Flyway history verified
              --> Device Service application healthy
              --> provisioning-only Gateway application healthy
```

This is a readiness safeguard rather than evidence of a formal Compose cycle.

## 4. Mandatory non-connections

The planned graphs intentionally omit:

- existing development Keycloak/realm/accounts/keys;
- existing MySQL, Kafka, InfluxDB, Docker networks, volumes, and service endpoints;
- ML inference/worker, Alert Service, Insight Service, simulator, event generator, replay engine, and real REFIT data;
- any global/legacy ingestion token or matching by source household number.

The full Task 4C scope keeps Alert/Insight upstream routes fail-closed; it does not authorize their invocation. The planned smoke test must not publish any ingestion or Kafka event and must not trigger model or alert workflows.

## 5. Verified versus unresolved graph elements

| Element | Status | Evidence or reason |
|---|---|---|
| Full Task 4C eight-service graph | Verified | `experiments/refit_task4c_deployment_preparation/docker-compose.refit.yml` |
| MySQL/Influx Compose health checks | Verified | `docker-compose.refit.yml:18-22,72-76` |
| App/Kafka only `service_started` dependencies | Verified | `docker-compose.refit.yml:97-99,117-119,140-144,166-174,208-216` |
| Provisioning-only composition | Proposed / not implemented | Required to remove the operational loop; needs future static review. |
| Isolated OIDC provider and persistent identity store | Proposed / not implemented | Task 4C has no issuer service; Task 4D documented the missing design. |
| Same-volume MySQL state handoff | Proposed / unapproved | Avoids loss of generated IDs; concurrent use and volume naming must be explicitly designed. |
| Device-secret issuance path | Unresolved | Backend has no issuance/persistence/rotation API. |
