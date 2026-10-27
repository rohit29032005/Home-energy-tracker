# Task 4H Stage R0 — Backup and Rollback Plan

## Scope and decision boundary

This is an evidence-based, planning-only assessment. No backup, export,
snapshot, copy, restore, rollback test, Docker lifecycle action, database
query, endpoint request, or configuration change was performed.

**Current backup/rollback decision: UNRESOLVED.** A consistent backup and a
tested rollback capability have not been established.

## Finding labels

- **VERIFIED** — directly supported by read-only metadata/source evidence.
- **INFERRED** — a technically plausible consequence, not observed directly.
- **UNRESOLVED** — evidence is insufficient or outside this task's safe scope.
- **RECOMMENDED** — a future approval-gated control; it was not executed.

## Evidence reviewed

- Task 4F network/volume and startup findings.
- Task 4G data-and-initialization risk assessment and recovery plan.
- Non-secret Docker volume/container metadata reviewed during Task 4I.
- Static docker-compose.yml storage declarations and User Service Flyway
  configuration.

## Persistent-state inventory

| Classification | Asset | Evidence | Backup/rollback implication |
|---|---|---|---|
| **VERIFIED** | MySQL data | Named volume home-energy-tracker_db-data is attached to the running, Docker-healthy MySQL container. | It contains existing relational application state and must not be reset, recreated, or copied live as an assumed consistent filesystem backup. |
| **VERIFIED** | Kafka broker state | Named volume home-energy-tracker_kafka-data is attached to stopped Kafka; auxiliary internal mounts are also attached. | Broker data, metadata, topics, and consumer state may be retained. All required broker state must be preserved together. |
| **VERIFIED** | InfluxDB time-series state | Named volume home-energy-tracker_influx-data is attached to stopped InfluxDB; an auxiliary configuration mount also exists. | Data and required configuration state must be captured as one recovery point. |
| **VERIFIED** | Monitoring state | Named Grafana and Prometheus data volumes exist. | Include only if monitoring continuity is inside the rollback objective. Do not delete/recreate them. |
| **VERIFIED** | Keycloak import source | A read-only realm-import bind mount exists; no dedicated named Keycloak database volume is declared in Compose. | Identity persistence behavior cannot be assumed. Treat it as a separate recovery gate. |
| **VERIFIED** | Project artifacts | docker-compose.yml, application configuration, migration scripts, and service source are present in the workspace. | Record a non-secret source/configuration revision manifest before a future backup; do not copy or alter artifacts during this task. |
| **INFERRED** | Repository-managed backup tooling | Static repository review did not establish a supported backup/restore automation. | A manual/external operating procedure may exist, but none was verified in the workspace. |
| **UNRESOLVED** | External backup destination, retention, encryption, owner, and recovery-point objective | These are outside the inspected workspace and were not queried. | Recovery cannot rely on an unspecified or unverified external backup process. |

Supporting evidence: Task 4F network_volume_port_audit.md section 2;
Task 4G data_and_initialization_risks.md, persistent-state inventory;
docker-compose.yml service/volume declarations.

## Consistency constraints

### MySQL

- **VERIFIED:** MySQL is running and a persistent data volume is attached.
  Docker health only proves the database container health check, not that
  application writes are quiesced.
- **INFERRED:** A direct filesystem copy of a live database directory is not a
  verified transaction-consistent backup method.
- **UNRESOLVED:** Table storage engines, active writers, transaction state,
  binary-log requirements, database size, and current Flyway history were not
  inspected because database queries and backup actions are out of scope.
- **RECOMMENDED:** Before a future backup, obtain a maintenance/write-quiesce
  decision and use a MySQL-aware method. A transaction-consistent logical
  export is suitable only after transactional-engine compatibility is verified;
  otherwise use an approved vendor-supported physical method or controlled
  quiesce/lock-and-snapshot procedure.

### Kafka

- **VERIFIED:** Kafka is stopped after OOMKilled=true / exit 137 and retains
  named broker data plus auxiliary mounts.
- **INFERRED:** Because the broker is stopped, a future cold capture can be
  byte-consistent only if every required broker-state mount is captured
  together, ownership/metadata are retained, and no broker process is started
  during capture.
- **UNRESOLVED:** Log-recovery condition after the OOM, topic retention,
  consumer offsets, exact image compatibility, and operational recoverability
  have not been demonstrated.
- **RECOMMENDED:** Preserve the broker data volume and all required
  configuration state. Verify any restore only in a separate, isolated broker
  environment with producers and consumers disabled.

### InfluxDB

- **VERIFIED:** InfluxDB is stopped and retains a named data volume plus an
  auxiliary configuration mount.
- **INFERRED:** A cold capture can be internally consistent only if data and
  required configuration are captured together while no process accesses them.
- **UNRESOLVED:** Current initialization/bucket state and a supported restore
  procedure were not verified.
- **RECOMMENDED:** Preserve data/configuration together and validate an
  isolated restore before any primary-volume replacement is considered.

### Identity and monitoring

- **VERIFIED:** Grafana and Prometheus volumes are persistent. Keycloak uses a
  realm-import bind mount and has no declared named database volume.
- **UNRESOLVED:** Keycloak identity-state persistence and a safe identity
  rollback method are not established.
- **RECOMMENDED:** Do not recreate Keycloak as part of a backup exercise.
  Include monitoring volumes only if rollback scope explicitly requires them.

## Proposed future backup, verification, and rollback procedure

This procedure is **RECOMMENDED only** and was not executed.

1. **Authorization and scope:** Obtain explicit approval for a maintenance
   window, backup destination, retention/access controls, rollback authority,
   and exclusion of REFIT Task 4C.
2. **Pre-backup manifest:** Record non-secret container/image/volume
   identities, service state, and source/configuration revision. Do not record
   credentials or device tokens.
3. **MySQL consistency gate:** Establish write quiescence and table-engine
   suitability. Use an approved MySQL-aware backup method, not a live
   filesystem copy of the data directory.
4. **Kafka cold capture:** Keep Kafka stopped; capture all required broker
   state as one recovery point while preserving protected secret material
   through a separately approved secret-management process.
5. **Influx cold capture:** Capture data and configuration state together while
   InfluxDB remains stopped. Do not allow initialization/reset.
6. **Artifact verification:** Create an approved manifest and integrity hashes,
   confirm readability/completeness, and store artifacts separately from the
   original volumes.
7. **Isolated restore test:** Restore only to fresh isolated targets. Validate
   relational schema/migration state, Kafka log recovery with consumers
   disabled, and expected Influx metadata/time-series availability.
8. **Rollback decision:** Do not overwrite original volumes. A rollback can be
   authorized only after the isolated restore test passes and the recovery
   authority accepts the result.
9. **Abort:** Stop if quiescence, compatibility, artifact integrity, isolated
   restore, Kafka resource safety, or identity persistence cannot be shown.

## Verification and rollback criteria

| Criterion | Current status | Required future evidence |
|---|---|---|
| Backup artifact exists | **UNRESOLVED — not created** | Approved artifact manifest and integrity verification. |
| MySQL consistency | **UNRESOLVED** | Write/quiesce evidence and method-specific consistency validation. |
| Kafka capture completeness | **UNRESOLVED** | All broker-state mounts preserved; isolated broker recovery evidence. |
| Influx capture completeness | **UNRESOLVED** | Data/configuration captured together and isolated restore checks. |
| Restore test | **UNRESOLVED — not performed** | Fresh isolated restore, integrity checks, and accepted results. |
| Primary rollback | **UNRESOLVED — not performed** | Explicit authority plus successful isolated restore test. |

## Stage R0 conclusion

**NO-GO for service recovery.** The persistent-state inventory is
evidence-backed, but no backup or rollback test has been performed. A
consistent, verified, and recoverable backup capability remains a prerequisite
before any action that could migrate, recreate, initialize, or process retained
state.

