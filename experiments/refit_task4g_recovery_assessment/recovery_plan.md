# Proposed Staged Recovery Plan — Approval Required Before Execution

## Status of this document

This is a **plan only**. Task 4G did not start, restart, create, remove, or
reconfigure any Docker resource. Every stage below requires a separate,
explicit approval before execution. The plan is intentionally narrower than a
Compose-wide startup to protect retained database, broker, telemetry, and
identity state.

## Recovery objective

Restore the existing Home Energy Tracker in a controlled order while preserving
current persistent state and preventing unreviewed database migrations,
simulated telemetry, historical Kafka processing, anomaly processing, and
notifications. REFIT Task 4C is outside this plan and remains independently
blocked.

## Stage R0 — Pre-recovery protection and evidence collection

**Purpose:** Establish a recoverable baseline before any lifecycle action.

**Approval required:** Approval to perform non-destructive backup/readiness
preparation and inspect non-secret operational state.

**Required actions after approval:**

1. Record immutable identifiers/status for existing named volumes and
   containers; do not remove, recreate, or prune them.
2. Define and verify a backup/rollback procedure for existing MySQL, Kafka,
   and InfluxDB persistent data before their dependent services start.
3. Review User Service Flyway history and pending-migration impact using a
   controlled, non-secret procedure.
4. Confirm, without exposing values, that Ingestion Service effective
   simulation is disabled.
5. Define expected broker readiness, application readiness, and abort evidence
   for subsequent stages.

**Exit criteria:** Backup/rollback plan accepted; no unresolved uncertainty
about simulator activation; a safe Kafka resource plan exists; no broad Compose
action is planned.

**Abort conditions:** Backup cannot be made/verified, a pending migration has
unknown impact, effective simulation may be enabled, or Kafka resource limits
cannot be justified.

## Stage R1 — Kafka broker-only recovery

**Purpose:** Recover the existing broker only after addressing its recorded OOM
termination.

**Approval required:** Explicit approval to start the exact existing Kafka
container, with a documented Docker Desktop/host resource budget and a
broker-only observation period.

**Required actions after approval:**

1. Preserve home-energy-tracker_kafka-data and do not recreate the broker or
   its data volume.
2. Apply only an approved capacity remedy; do not guess a JVM or Docker memory
   setting.
3. Start only the existing Kafka broker, not the full Compose project and not
   downstream consumer services.
4. Observe broker stability/readiness using approved non-secret diagnostics.
5. Stop the stage safely if memory pressure, broker recovery errors, or
   unexpected persistent-data issues occur.

**Exit criteria:** Broker is stable for the approved observation window,
resource use remains inside the approved budget, and no data-volume
reinitialization occurred.

**Abort conditions:** Another OOM event, unstable broker process, topic/log
recovery failure, unexplained resource pressure, or an indication that a volume
would need recreation.

## Stage R2 — Independent platform dependencies

**Purpose:** Restore prerequisites that do not process application telemetry.

**Approval required:** Separate approval for each service start and readiness
inspection.

**Proposed order:**

1. Retain MySQL as the currently healthy prerequisite; do not restart it just
   to normalize state.
2. Recover InfluxDB only after confirming its existing volume/init behavior and
   rollback protection.
3. Recover Keycloak only after confirming local import/persistence behavior and
   an identity rollback approach.
4. Recover Mailpit only if Alert Service recovery will later be authorized.
5. Treat Kafka UI as optional operational visibility, not proof that the Kafka
   broker is ready.

**Exit criteria:** Each approved dependency demonstrates defined
application-level readiness; no service was recreated; MySQL remains healthy.

**Abort conditions:** Identity import/persistence is ambiguous, InfluxDB
attempts reinitialization, or a dependency requires destructive cleanup.

## Stage R3 — Database-backed core services

**Purpose:** Restore the identity/device control plane only after database
protection is in place.

**Approval required:** Explicit approval for migration-aware User Service
start, then Device Service start.

**Proposed order:**

1. Start User Service only after the Flyway review and backup gate in R0.
2. Confirm its application readiness and observe migration results before
   proceeding.
3. Start Device Service after User Service and MySQL are demonstrably ready.
4. Confirm readiness with approved checks before opening event-processing
   services.

**Exit criteria:** User and Device Services function without unexpected
migration, schema, or record changes.

**Abort conditions:** Migration validation/application is unexpected,
application startup conflicts with retained database state, or device records
are missing/inconsistent.

## Stage R4 — Event-processing services with side-effect controls

**Purpose:** Recover data-plane services without unintentionally generating or
processing telemetry, anomalies, alerts, or emails.

**Approval required:** Separate approval accepting the assessed Kafka
backlog/offset behavior and notification implications.

**Proposed sequence and gates:**

1. **Ingestion Service:** Start only after simulation is confirmed disabled and
   User, Device, and Kafka prerequisites are ready.
2. **Usage Service:** Start only after authorization for Kafka consumption,
   InfluxDB writes, scheduled aggregation, and possible alert publication.
3. **Alert Service:** Start only after approval for persisted alerts and
   possible email attempts through Mailpit.
4. **Insight Service:** Start only after Usage Service behavior is stable.
5. **ML Inference Service:** Defer until core recovery has stabilized. Start
   only after separate approval for Kafka consumption and anomaly publication.

**Exit criteria:** Each service remains stable through the approved observation
period; no unapproved simulator traffic, backlog processing, anomaly result,
alert write, or mail side effect occurs.

**Abort conditions:** Simulation is observed, unexpected consumer backlog
processing begins, alerts/emails are emitted unexpectedly, or Kafka/InfluxDB
stability deteriorates.

## Stage R5 — Gateway, user interface, and monitoring

**Purpose:** Restore access and observability only after backend and identity
dependencies are ready.

**Approval required:** Approval for gateway/UI/monitoring start and any
subsequent endpoint-health validation. Task 4G itself made no HTTP call.

**Proposed order:**

1. API Gateway after Keycloak, User, Device, Ingestion, Usage, Alert, and
   Insight satisfy their approved readiness criteria.
2. Frontend after API Gateway is ready.
3. Prometheus after Gateway is ready; Grafana after Prometheus is ready.

**Exit criteria:** Access and monitoring are recovered without masking an
unhealthy dependency; health evidence is captured under its own approval.

**Abort conditions:** Gateway dependency failure, authentication inconsistency,
or monitoring startup indicates core services are unstable.

## Mandatory guardrails for every future stage

- Never use a project-wide docker compose up as a recovery shortcut.
- Never use docker compose down -v, volume pruning, database resets, or
  container recreation as a troubleshooting shortcut.
- Do not run REFIT Task 4C provisioning, deployment, or replay as part of
  existing-stack recovery.
- Do not treat a running container or service_started as proof of application
  readiness.
- Record stage evidence and stop at the first unexpected migration, OOM,
  initialization, consumer-processing, or notification side effect.
- Keep secrets, credentials, and device tokens out of commands, logs, and
  recovery reports.

## Approval decision requested before implementation

The next safe decision is **not** a bulk recovery. It is whether to authorize
Stage R0 only: backup/rollback preparation, non-secret configuration safety
verification, and Kafka capacity planning. After R0 evidence is reviewed, a
new explicit approval is still required before Stage R1 (Kafka broker-only
start) or any later service action.

