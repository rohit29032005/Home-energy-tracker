# Task 4J — Backup Execution Readiness and Rollback Gate

## Purpose and strict boundary

This report prepares a narrowly scoped, approval-gated procedure for a future
backup and isolated restore test of the existing Home Energy Tracker. It is not
a backup procedure execution record.

**No backup, export, snapshot, copy, restore, rollback, container lifecycle
action, Compose action, database query, migration, endpoint request,
configuration change, telemetry replay, alert, notification, or REFIT Task 4C
action was executed by Task 4J.**

## Finding labels

- **VERIFIED** — directly supported by read-only Docker/source/Task 4F-4H
  evidence.
- **INFERRED** — a technically plausible consequence, not observed directly.
- **UNRESOLVED** — evidence is insufficient or a necessary action is outside
  this task's authorization.
- **RECOMMENDED** — a future approval-gated control; it was not executed.

## Evidence reviewed

- Task 4F network/volume and runtime reports.
- Task 4G data/initialization risks and Kafka diagnosis.
- Task 4H backup/rollback, Kafka, Flyway, simulation, prerequisites, and final
  decision reports.
- Static docker-compose.yml storage/service declarations and static service
  configuration, inspected without exposing secret values.
- Current non-secret Docker metadata for MySQL and persistent-state attachment.

## Proposed backup scope — not yet human-approved

The following is the **exact scope proposed for approval**, not a claim that an
approved backup already exists.

| Scope item | Classification | Evidence / boundary | Proposed treatment |
|---|---|---|---|
| MySQL application schema and data | **VERIFIED** | Existing MySQL container is mysql:8.3.0, running/healthy, with home-energy-tracker_db-data mounted at /var/lib/mysql. Static application configuration identifies the home_energy_tracker application schema. | Mandatory. Capture schema/data plus relevant triggers, routines, events, and Flyway history only after a MySQL consistency gate is approved. |
| MySQL system/account metadata | **UNRESOLVED** | Static evidence does not establish whether account/grant metadata is required for recovery. | Human decision required. Do not blindly include or restore the MySQL system schema. |
| Kafka broker state | **VERIFIED** | Stopped Kafka retains home-energy-tracker_kafka-data plus auxiliary internal mounts. | Mandatory. Preserve every required broker-state mount, compatible image identity, and a non-secret configuration manifest together. |
| InfluxDB time-series state | **VERIFIED** | Stopped InfluxDB retains home-energy-tracker_influx-data plus an auxiliary configuration mount. | Mandatory. Preserve data and required configuration/state together as a single recovery point. |
| Keycloak-related state | **VERIFIED import source; UNRESOLVED runtime identity state** | Compose declares a read-only realm-import bind mount and no named Keycloak database volume. | Mandatory human decision: preserve the import artifact, then decide whether reproducible-import-only is sufficient or a separately evidenced identity-state backup is required. |
| Grafana and Prometheus state | **VERIFIED** | Named monitoring volumes exist. | Optional; include only if monitoring continuity is part of the agreed rollback objective. |
| Non-secret configuration/source manifest | **VERIFIED** | Compose, static application configuration, migrations, and source artifacts exist. | Mandatory. Record source revision, migration hashes, image identities/digests, volume identities, and service state. Exclude credentials/tokens. |
| Secrets and credentials | **VERIFIED exclusion** | This task intentionally did not inspect secret values. | Never place secret values in manifests, report text, filenames, or command lines. Use a separately approved secure secret-management process. |
| REFIT Task 4C | **VERIFIED exclusion** | No Task 4C container, network, or volume exists. | Exclude completely. Existing-stack backup/recovery approval never authorizes REFIT provisioning, deployment, or replay. |

Supporting evidence: Task 4F network_volume_port_audit.md section 2;
Task 4H backup_rollback_plan.md; Task 4H recovery_prerequisites.md;
docker-compose.yml service/volume declarations.

## MySQL-aware backup gate

### Verified facts

- **VERIFIED:** MySQL runs the mysql:8.3.0 image, has Docker health status
  healthy, restart policy always, a published database port, and a persistent
  data volume.
- **VERIFIED:** User Service owns Flyway migrations; static migrations V1-V7
  include schema creation, schema alteration, index creation, and seed-data
  operations.
- **VERIFIED:** A raw copy of the live MySQL data directory is not accepted as
  a verified transaction-consistent backup method.

### Unresolved eligibility evidence

The following cannot be established from Docker metadata/static source alone:

1. Storage engines for every relevant table.
2. Active/external writers and open transactions.
3. Binary-log, replication, point-in-time recovery, size, and privilege needs.
4. Current Flyway history, pending versions, checksums, and schema/seed state.
5. Approved backup destination, retention, encryption, access owner, RPO, RTO,
   backup operator, and rollback authority.

### Proposed MySQL-aware method

**RECOMMENDED, future approval only:**

1. Authorize a maintenance/write-quiescence decision and a separate
   non-destructive database eligibility assessment.
2. Limit application-data scope to the home_energy_tracker schema, including
   schema/data, needed triggers, routines, events, and Flyway history. Decide
   separately whether grants/accounts are required.
3. If all relevant tables are confirmed transactional/InnoDB, consistent
   snapshot privileges are available, and DDL/writes are controlled, use a
   MySQL-8.3-compatible logical consistent-snapshot method, including the
   method-specific schema/data/routine/event/trigger options.
4. If any relevant table is nontransactional, any necessary privilege is
   unavailable, or writes/DDL cannot be controlled, do not rely on a
   single-transaction logical snapshot. Select an approved write-quiesce/lock
   strategy or a vendor-supported physical backup method.
5. Place the artifact on a separately approved, access-controlled destination.
   Never use the original MySQL volume as the backup destination and never
   overwrite it during an isolated test.

This is deliberately conditional: Stage R0 did not establish the database facts
needed to choose one method safely.

## Kafka and InfluxDB preservation gate

### Kafka

- **VERIFIED:** Kafka is stopped after OOMKilled=true / exit 137, retains
  persistent broker data, and has auxiliary mounts.
- **INFERRED:** A cold capture can be byte-consistent only if every required
  broker-state mount is captured together, metadata/ownership are retained,
  and the broker remains stopped during capture.
- **UNRESOLVED:** Broker log/metadata recovery condition, topics, consumer
  offsets, exact runtime image identity, and safe capacity plan.
- **RECOMMENDED:** Preserve source broker state without reset, format,
  recreation, or overwrite. A future isolated restore must use fresh storage,
  a controlled compatible image identity, no original network/volumes, and no
  producer, consumer, Kafka UI, alert, ML, or application side effect.

### InfluxDB

- **VERIFIED:** InfluxDB is stopped and retains named data plus an auxiliary
  configuration mount.
- **INFERRED:** A cold capture can be internally consistent only when data and
  required configuration/state are captured together while no service accesses
  them.
- **UNRESOLVED:** Initialization/bucket state and supported restore behavior.
- **RECOMMENDED:** Preserve data/configuration as one recovery point and test
  restoration only in a fresh isolated target. Do not reset/recreate or replace
  the original volume.

### Keycloak-related state

- **VERIFIED:** A read-only realm-import artifact is configured.
- **UNRESOLVED:** Whether live identity state exists outside that artifact, and
  whether it is in the MySQL scope, is not established.
- **RECOMMENDED:** Require an explicit human scope decision before backup:
  import-source preservation only, or a separate identity-state recovery plan.
  Do not describe the import artifact as a backup of live identities without
  supporting evidence.

## Exact human decisions required before backup execution

| Decision | Why it is required | Approval required from |
|---|---|---|
| Backup scope and recovery objective | Determines whether monitoring, account/grant metadata, and Keycloak identity behavior are in scope. | Project/data owner. |
| RPO, RTO, retention, and deletion policy | Defines the acceptable recovery point, lifetime, and disposal of backup artifacts. | Project/data owner. |
| Backup destination, encryption, key custody, and access control | Prevents artifacts or secrets being stored insecurely. | Project/data owner plus authorized security/storage owner. |
| Maintenance/write-quiescence window | MySQL consistency cannot be assumed while writers/DDL are unknown. | Project owner and authorized database operator. |
| MySQL eligibility and method selection | Determines whether logical consistent snapshot is suitable or a quiesce/physical method is required. | Authorized database operator after approved read-only assessment. |
| Kafka cold-capture and broker-state scope | Ensures all required mounts/configuration are preserved without data loss. | Project owner and authorized infrastructure operator. |
| InfluxDB init/restore scope | Prevents unintended initialization/reset of time-series state. | Project owner and authorized infrastructure operator. |
| Keycloak identity scope | Resolves import-source-only versus live identity-state requirements. | Project owner/identity owner. |
| Isolated restore-test environment | Ensures a fresh disposable target cannot attach/overwrite originals or emit events. | Project owner and authorized recovery operator. |
| Rollback authority | Prevents any primary-volume overwrite without explicit acceptance. | Project/data owner. |
| Kafka recovery and application startup | OOM/capacity, consumers, Flyway, alert, ML, and notification gates are independent. | Separate explicit approval; not part of backup authorization. |
| REFIT Task 4C | It remains isolated/undeployed and outside the existing-stack plan. | Separate REFIT approval only. |

## Proposed approval-gated sequence

This is a future sequence; none of these steps ran in Task 4J.

1. **Approve scope and controls.** Accept the scope table, owners, RPO/RTO,
   destination, retention, encryption, access, and rollback authority.
2. **Prepare a non-secret manifest.** Record resource identities, volume
   identities, static configuration/source revision, migration hashes, image
   identities, and service state. Do not capture secret values.
3. **Approve MySQL eligibility assessment.** Determine table-engine and
   write-quiescence requirements using a separately approved non-destructive
   procedure.
4. **Choose MySQL method.** Use the approved MySQL-aware method based on the
   eligibility result. Do not use live volume copying as a fallback.
5. **Capture stopped-state stores.** Capture Kafka and InfluxDB state only
   after their complete mount/configuration scope and destination controls are
   approved. Preserve originals unchanged.
6. **Verify artifacts.** Produce approved inventory/manifest, integrity hashes,
   readability/completeness evidence, and access-control confirmation.
7. **Restore only in isolation.** Use fresh disposable storage, network,
   ports, and compatible software. Never attach original volumes/networks or
   start Home Energy Tracker/REFIT consumers.
8. **Assess restoration.** Compare against pre-backup manifest and acceptance
   criteria. Do not perform primary rollback.
9. **Human acceptance.** Only a successful isolated restore test plus explicit
   rollback authority can permit planning a primary rollback. It still does not
   authorize Kafka/app recovery.

## Isolated restore-test acceptance criteria

| Area | Acceptance criterion | Safety boundary |
|---|---|---|
| Artifact integrity | Approved hashes/manifests match; artifact is complete/readable and separately stored. | Do not compare by mutating originals. |
| MySQL | Imports into a fresh MySQL-8.3-compatible disposable target without error; approved schema/object, Flyway-history, and data-integrity checks pass. | No primary volume attachment/overwrite; no application service start. |
| Kafka | Fresh isolated broker recovers logs/metadata with consumers/producers/UI disabled and records no original-volume write. | Kafka capacity/start is a separate approval; no existing broker start here. |
| InfluxDB | Fresh isolated target exposes expected metadata/time-series availability through approved non-writing validation. | No original volume replacement or setup reset. |
| Keycloak | Human-approved identity scope is met; import source is preserved and any live-state requirement is explicitly addressed. | Do not infer live identity recovery from import artifact alone. |
| Cross-system coherence | Manifest identifies the selected common recovery point/time and known non-atomic limitations. | Do not claim transactional atomicity across MySQL, Kafka, and InfluxDB. |
| Isolation | Test uses fresh disposable resources and cannot connect to existing Home Energy Tracker or REFIT Task 4C state. | No original network, volume, ports, consumer, producer, or notification side effects. |
| Rollback readiness | Test results, abort conditions, and authority are documented and accepted. | Primary rollback remains a separately approved operation. |

## Explicit separations

The following remain independent NO-GO gates and are not authorized by a future
backup approval:

- Kafka broker recovery, memory/JVM configuration, topic/group inspection, or
  consumer restart.
- User Service/Flyway startup or migration execution.
- Ingestion, Usage, Alert, Insight, ML, replay, telemetry, anomaly, mail, or
  notification processing.
- Keycloak restart or identity provisioning.
- REFIT Task 4C deployment, profile/device creation, credentials, or replay.

## Final decision

# NO-GO — BACKUP EXECUTION NOT AUTHORIZED.

A backup/rollback capability has been planned in sufficient detail for human
review, but no artifact, consistent backup, integrity verification, or isolated
restore test exists. Human decisions and separate approvals listed above are
required before any backup execution can begin.

