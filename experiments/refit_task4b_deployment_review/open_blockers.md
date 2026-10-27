# Task 4B — Open Blockers and Unresolved Questions

All items below are based on static review. They are not evidence of a failed deployment because no deployment was created or tested.

| ID | Item | Status | Evidence / reason | Required resolution before execution |
|---|---|---|---|---|
| B1 | No isolated Compose deployment specification exists | Blocker | Task 4B found only `docker-compose.yml` and `docker-compose.prod.yml`; both contain fixed names/volumes. | Approve creation of a new deployment-only Compose file with distinct names, ports, networks, volumes, and secret source. |
| B2 | Current Compose cannot be safely parallelized by project name alone | Blocker | Fixed `container_name` entries and named volumes are present in `docker-compose.yml:4-352`; production uses fixed `*-prod` names and `energy-net` (`docker-compose.prod.yml:7-328`). | Future specification must omit/prefix container names and namespace every volume/network. |
| B3 | Host-port allocation is unverified | Unresolved | Static review found current development mappings including 3306, 9092, 9094, 8070, 8072, 8025, 1025, 8180, 8080, 3000, 9090, and 3001. No live port inspection was performed in Task 4B. | Perform a later approved read-only host-port inventory and allocate different ports. |
| B4 | Device credentials have no application issuance/revocation API | Blocker | Tokens are static `IOT_INGESTION_DEVICE_TOKENS` configuration (`IngestionAuthorizationService.java:42-81,149-177`). | Approve secure external generation/storage of three device-bound tokens and a manual revoke-by-config/restart procedure. |
| B5 | Profile/device IDs do not yet exist | Expected blocker | No profile/device was created; current IDs cannot be reused or inferred from REFIT house numbers. | Create three profiles and devices only after approval; record returned IDs in a non-secret ledger. |
| B6 | Shared legacy ML consumer would process shared-broker telemetry | Blocker for shared stack | Legacy worker consumes `energy-usage` and emits `anomaly-results` (`ml-service/app/kafka_worker.py:102-170`). | Exclude ML/Alert from initial isolated deployment; require a later ML plan if inference is desired. |
| B7 | Separate controlled-REFIT worker is not a direct ingestion replacement | Unresolved / out of scope | It has a distinct payload schema and controlled artifact (`refit_kafka_worker.py:224-257`; `main.py:274-283`). | Obtain explicit protocol/model approval before considering it. |
| B8 | Existing API provides one timestamp only | Unresolved | `EnergyUsageDto` includes only `deviceId`, `energyConsumed`, and `timestamp` (`EnergyUsageDto.java:11-18`). | Preserve source timestamp/provenance in the future replay ledger and document the approved payload-time policy. |
| B9 | No verified idempotency guarantee | Blocker for actual replay | DTO/service show no idempotency key or receipt API (`EnergyUsageDto.java`; `IngestionService.java:24-35`). | Retain Task 3 conservative ambiguous-outcome policy; obtain approval before any network submission. |
| B10 | Application-scoped Influx/Kafka cleanup path is absent | Blocker for post-event cleanup | Usage only writes/queries Influx; no app deletion path was found. MySQL deletion does not erase time series. | Use separate broker/bucket/volumes and approve scoped infrastructure cleanup before later replay. |
| B11 | Isolated Keycloak issuer/JWK design is not specified | Blocker if UI/JWT provisioning is used | Development defaults include host issuer `localhost:8180` (`docker-compose.yml:287-288`). | Create an isolated Keycloak/realm configuration or define a non-UI admin provisioning alternative. |
| B12 | Health readiness for non-database services is not fully specified | Design blocker | Current Compose uses mostly `service_started`; static health checks are visible for MySQL/Influx (`docker-compose.yml:13-17,73-85`). | Define health/readiness gates in future isolated specification before any event stage. |

## Decision

The static evidence supports **GO FOR DEPLOYMENT PLANNING ONLY**, not execution. B1–B12 must be addressed or explicitly approved with bounded scope before any deployment is created.
