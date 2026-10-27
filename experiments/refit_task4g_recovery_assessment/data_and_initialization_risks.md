# Data and Initialization Risk Assessment

## Scope and evidence standard

This is a read-only assessment prepared for Task 4G. No container, database,
volume, network, application endpoint, configuration, or REFIT resource was
changed. A risk is marked **verified** only where it is supported by the
Task 4F audit, current Docker metadata, or repository source/configuration.
Items marked **unknown** require evidence before a recovery action is authorized.

## Verified persistent-state inventory

| State area | Verified evidence | Recovery risk | Required control before future action |
|---|---|---|---|
| MySQL application data | The existing named home-energy-tracker_db-data volume is present; MySQL is running and reports healthy. | Recreating, resetting, or applying unreviewed migrations could change relational records. | Preserve the volume, define backup/rollback, and review migration state under separate approval. |
| User Service migration path | user-service/src/main/resources/application.properties enables Flyway and disables Hibernate automatic DDL. The migration set includes schema and seed migrations. | Flyway can validate or apply pending migrations against the retained shared database. | Capture a safe backup point and review migration history/pending impact before start. |
| Device Service database access | Device Service depends on healthy MySQL and has Flyway disabled. | It relies on shared schema/data managed by User Service migrations. | Start only after User Service database state and readiness are demonstrated. |
| Kafka broker data | The existing named home-energy-tracker_kafka-data volume is present. Kafka exited with OOMKilled=true and exit code 137. | Broker recovery can expose retained messages, consumer offsets, and topic configuration. | Preserve the volume; establish capacity and recovery criteria before a consumer starts. |
| InfluxDB telemetry data | The existing named home-energy-tracker_influx-data volume is present. InfluxDB is stopped. | Incorrect setup/reinitialization can affect persisted time-series data. | Do not recreate or reset the volume. Confirm persistence behavior and backup/rollback first. |
| Keycloak identity state | Compose runs Keycloak in development/import mode with a read-only realm-import mount. A dedicated named Keycloak DB volume is not declared. | Realm import/persistence behavior across restart is unverified. | Treat identity recovery as a separate controlled stage; establish backing-store behavior first. |
| Monitoring state | Named Grafana and Prometheus data volumes exist; both containers are stopped. | Monitoring restart can change runtime/retention state, but is lower risk than core data. | Restore only after core services are stable; do not remove/recreate volumes. |
| REFIT experiment state | Task 4F and current inspection found no refit-task4c container, network, or volume. | None from a deployed REFIT environment because it does not exist. | Keep Task 4C separately gated. |

## Verified service-side effects after a future restart

| Component | Verified behavior | Why a restart can have side effects | Required approval gate |
|---|---|---|---|
| Ingestion Service | simulation.enabled conditionally activates continuous/parallel simulator code. Compose supplies a false fallback, but effective runtime configuration was not inspected. | A different effective value can generate telemetry; normal ingestion can publish usage events. | Verify non-secret effective configuration shows simulation disabled. |
| Usage Service | It consumes energy-usage, writes time-series points, and scheduled aggregation can publish energy-alerts. | Retained Kafka records or scheduled aggregation can create writes and alerts. | Review topic/offset consequences and authorize processing before start. |
| Alert Service | It consumes alert/anomaly events, persists alert records, and can attempt mail delivery. | Historical events can create records or send notifications after startup. | Confirm notification policy/backlog handling and authorize side effects. |
| ML Inference Service | Its enabled Kafka worker consumes energy-usage and publishes anomaly results. | It can process retained traffic and create events consumed by Alert Service. | Defer until Kafka/core recovery is stable; authorize inference separately. |
| Insight Service | It depends on Usage Service. | It depends on recovered usage data and event processing. | Defer until Usage Service behavior is known and stable. |
| API Gateway and frontend | Gateway depends on user, device, ingestion, usage, alert, insight, and Keycloak; frontend depends on Gateway. | They can make an incompletely recovered system appear ready. | Restore only after required backend and identity readiness is demonstrated. |

## Initialization and consistency risks

### 1. Shared shutdown versus Kafka-specific failure

**Verified:** Kafka stopped on 2026-10-11 with exit code 137 and OOMKilled=true.
Most other stopped project containers have exit code 255 and the same later
finish-time pattern after the Docker interruption. MySQL and Kafka UI restarted
automatically because their restart policies permit it.

**Interpretation:** The shared later stop pattern does not prove an
application-level failure in every service. Kafka's earlier OOM termination is
a separate blocker and must not be hidden by starting the full Compose project.

### 2. Compose ordering is not readiness

**Verified:** MySQL and InfluxDB are the only services with Compose health
checks. Most depends_on relations use service_started, which orders start but
does not prove an application is ready to accept work.

**Risk:** A broad startup can cause dependent services to fail, retry, or
initialize while prerequisites are not operational.

**Control:** An approved recovery must use observable application readiness
criteria rather than treating a running container as healthy.

### 3. Kafka retained-event processing

**Verified:** Kafka uses persistent broker data; Usage, Alert, and ML contain
Kafka consumer/producer paths.

**Unknown:** Topic retention, consumer offsets, actual backlog, and effective
auto-topic/consumer settings were not inspected during this audit.

**Risk:** Starting a consumer after broker recovery can process pre-existing
events and create telemetry, anomaly, alert, database, or mail side effects.

**Control:** Preserve broker data and require approved consumer-backlog
assessment before any event-consuming service starts.

### 4. Database migration and seed behavior

**Verified:** User Service enables Flyway and disables Hibernate automatic DDL.
The repository includes schema and seed migrations.

**Unknown:** Current Flyway schema history and whether pending migrations exist
on the retained MySQL volume.

**Risk:** Startup can validate or apply migrations and change the existing
relational database.

**Control:** Require backup/rollback approval and migration-impact review; do
not start User Service merely as a connectivity test.

### 5. Identity and telemetry initialization uncertainty

**Verified:** Keycloak is configured as a development/import service and
InfluxDB has an existing persistent volume.

**Unknown:** The exact persisted identity realm state and InfluxDB
initialization status were intentionally not inspected at credential level.

**Risk:** Treating either service as stateless can overwrite, re-import, or
misinterpret persisted application state.

**Control:** Do not recreate either service or volume. Establish a
service-specific recovery procedure before any approved action.

## Non-negotiable data-protection constraints

The following remain prohibited unless separately and explicitly approved after
a backup/rollback plan is accepted:

- docker compose down -v, volume removal, pruning, database reset, or
  container recreation that changes retained storage.
- Broad docker compose up actions that start multiple consumers and
  initialization paths together.
- REFIT device/profile/token provisioning, replay, or deployment.
- Unreviewed migration execution, simulation activation, consumer processing,
  or alert/email processing.

## Residual risks requiring evidence

| ID | Status | What is not yet known | Why it matters |
|---|---|---|---|
| RISK-01 | Open | Root cause and safe resource budget for Kafka OOM. | Broker recovery can fail again or destabilize Docker Desktop. |
| RISK-02 | Open | MySQL backup/rollback mechanism and current migration history. | User Service start can write to the shared database. |
| RISK-03 | Open | Kafka topic backlog, consumer offsets, and replay side effects. | Usage, Alert, and ML can create writes/notifications. |
| RISK-04 | Open | Effective simulation setting for Ingestion Service. | An unverified setting can generate telemetry. |
| RISK-05 | Open | Keycloak and InfluxDB persistent initialization behavior. | Incorrect recovery can affect identity or time-series state. |
| RISK-06 | Open | Readiness evidence for services without a health check. | service_started alone is insufficient for safe staged recovery. |

## Assessment conclusion

Existing persistent data must be treated as production-like local state. The
volumes remain unmodified by Task 4G, but safe recovery requires
approval-gated preparation for Kafka capacity, database migration protection,
identity/telemetry persistence, and event-consumer side effects. No REFIT
action is authorized by this assessment.

