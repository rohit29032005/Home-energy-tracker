# Task 4K — Human Approval Register and Backup Preflight

## Purpose and safety boundary

This register converts Task 4J unresolved decisions into named approval gates.
It records missing approvals; it does not infer consent from silence, existing
container state, or prior planning documents.

**No backup, restore, rollback, Docker lifecycle action, Compose action,
database query, migration, configuration change, endpoint request, replay,
telemetry, alert, notification, or REFIT Task 4C action was performed.**

## Status terms

- **VERIFIED** — supported by Task 4F-4J read-only evidence.
- **UNRESOLVED** — required evidence or decision does not yet exist.
- **RECOMMENDED** — a future control/sequence only.
- **APPROVAL MISSING** — no explicit human authorization is recorded.

## Approval decision matrix

| ID | Human decision | Decision owner role | Current status | Evidence required before decision | Explicit approval missing? |
|---|---|---|---|---|---|
| A-01 | Confirm recovery objective and backup scope: MySQL application data, Kafka, InfluxDB, Keycloak-related state, configuration manifest, and whether monitoring is included. | Project/data owner | **UNRESOLVED** | Task 4J scope table; data classification and recovery objective. | **Yes** |
| A-02 | Decide whether MySQL system/account/grant metadata is in scope. | Project/data owner with database owner | **UNRESOLVED** | Recovery dependency review; do not blindly include MySQL system schema. | **Yes** |
| A-03 | Set RPO, RTO, retention period, deletion/disposal policy, and backup naming/manifest standard. | Project/data owner | **UNRESOLVED** | Defined business/research recovery objective and storage policy. | **Yes** |
| A-04 | Approve destination, encryption at rest, key custody, least-privilege access, and artifact operator. | Project/data owner with authorized security/storage owner | **UNRESOLVED** | Approved storage design; key/access process; no secret values in artifacts/logs. | **Yes** |
| A-05 | Approve MySQL read-only eligibility assessment for storage engines, writers, privileges, size, binary-log/PITR requirements, and Flyway history impact. | Authorized database operator | **UNRESOLVED** | Task 4J MySQL gate; explicit scope limited to non-destructive assessment. | **Yes** |
| A-06 | Choose MySQL backup method after A-05: consistent logical snapshot only if eligibility is proven; otherwise approved quiesce/lock or vendor-supported physical method. | Project owner plus authorized database operator | **UNRESOLVED** | A-05 results and MySQL 8.3 method suitability. | **Yes** |
| A-07 | Approve maintenance/write-quiescence controls for actual MySQL backup. | Project owner plus authorized database operator | **UNRESOLVED** | Active-writer/DDL decision, backup window, abort conditions. | **Yes** |
| A-08 | Approve Kafka cold-capture scope: data volume, all required broker-state mounts, compatible image identity, non-secret configuration manifest, and protected-secret process. | Project owner plus authorized infrastructure operator | **UNRESOLVED** | Task 4J Kafka preservation plan; no reset/reformat/recreate guarantee. | **Yes** |
| A-09 | Approve InfluxDB cold-capture scope: data plus all required configuration/state, no initialization/reset, and restore method. | Project owner plus authorized infrastructure operator | **UNRESOLVED** | Task 4J Influx preservation plan and init-state limitation. | **Yes** |
| A-10 | Decide Keycloak identity scope: preserve import source only or establish a separate live identity-state recovery plan. | Project owner with identity owner | **UNRESOLVED** | Read-only realm-import evidence; no declared named Keycloak DB volume. | **Yes** |
| A-11 | Decide whether Grafana/Prometheus continuity is inside backup/rollback scope. | Project/data owner | **UNRESOLVED** | Monitoring recovery objective and storage cost/benefit. | **Yes** |
| A-12 | Approve a fresh isolated restore-test environment and its isolation constraints. | Project owner plus authorized recovery operator | **UNRESOLVED** | Disposable volumes/network/ports; no connection to original HET/REFIT state; no consumers/producers/notifications. | **Yes** |
| A-13 | Accept restore-test criteria and authorize primary rollback authority only after a passing isolated test. | Project/data owner | **UNRESOLVED** | Artifact integrity, isolated restore result, abort evidence, and signed acceptance record. | **Yes** |
| A-14 | Keep Kafka recovery, Flyway execution, app startup, replay, alerts, notifications, and ML processing separate from backup approval. | Project owner | **VERIFIED separate gate** | Task 4H prerequisite register and final NO-GO. | **Yes, for each future action** |
| A-15 | Keep REFIT Task 4C isolated/undeployed and outside backup scope. | Project owner | **VERIFIED separate gate** | Task 4H-FINAL read-only resource check found no Task 4C resources. | **Yes, separate REFIT approval required** |

## Verified preflight facts

- **VERIFIED:** MySQL is running/healthy on mysql:8.3.0 and has a persistent
  volume. It is not safe to accept a live raw filesystem copy as a consistent
  backup.
- **VERIFIED:** Kafka is stopped after OOMKilled=true / exit 137 and retains
  persistent broker data; its recovery/capacity issue is separate from backup.
- **VERIFIED:** InfluxDB is stopped and retains persistent data plus
  configuration state.
- **VERIFIED:** Keycloak has a read-only realm-import source but its full live
  identity persistence is not established.
- **VERIFIED:** User Service Flyway and downstream Kafka consumers can create
  migration/event/alert side effects after future service starts.
- **UNRESOLVED:** No consistent backup artifact, integrity verification, or
  isolated restore test exists.
- **UNRESOLVED:** No human decision in A-01 through A-13 is recorded.

Supporting evidence: Task 4J backup_execution_readiness.md; Task 4H
backup_rollback_plan.md, recovery_prerequisites.md, and final_go_no_go.md.

## Read-only preflight activities after separate authorization

The following are **RECOMMENDED** only after an explicit, narrowly scoped
authorization. They do not create a backup by themselves, but some require
privileged read access and therefore cannot be assumed safe without owner
approval.

| Assessment | Classification | Needs maintenance window? | Separate authorization needed? | Boundary |
|---|---|---:|---:|---|
| Record non-secret source revision, image identity, volume identity, and service-state manifest. | **RECOMMENDED** | No, if it remains metadata-only. | Yes. | Do not inspect environment values or secret material. |
| Review backup destination capacity, retention, encryption process, and access-control design. | **RECOMMENDED** | No. | Yes. | Do not create artifacts, keys, buckets, or permissions in this preflight. |
| MySQL read-only eligibility assessment, including storage-engine and Flyway-history impact. | **RECOMMENDED** | Not normally, but owner must decide if read access is acceptable. | Yes, database-operator approval. | No migrations, locks, exports, or data changes. |
| Review Kafka/Influx mount scope and compatible image/configuration manifest. | **RECOMMENDED** | No, if metadata-only. | Yes. | Do not read secret mount contents or start a service. |
| Define isolated restore target design, capacity, ports, and isolation rules. | **RECOMMENDED** | No. | Yes. | Do not create test containers, volumes, networks, or configuration. |
| Review Keycloak import artifact scope without opening secrets. | **RECOMMENDED** | No. | Yes, identity-owner approval. | Do not recreate Keycloak or claim live-state coverage. |

## Activities that require a maintenance or controlled change window

| Activity | Why a controlled window is required | Separate gate |
|---|---|---|
| Actual MySQL backup | Consistency requires an approved write/DDL/quiescence decision and a method based on A-05 eligibility. | A-06 and A-07. |
| Kafka cold capture | Preserve complete broker state while ensuring no broker/process accesses state; do not alter originals. | A-08 and Kafka recovery remains separate. |
| InfluxDB cold capture | Preserve data and configuration together without initialization/reset. | A-09. |
| Isolated restore test | Uses new disposable resources and must be change-controlled, even though it must not affect the existing stack. | A-12. |
| Primary rollback | Can overwrite operational state and therefore requires accepted restore evidence and explicit authority. | A-13. |

## Exact human decisions required next

1. Approve or revise the proposed backup scope in A-01, including the optional
   monitoring scope and the unknown Keycloak identity scope.
2. Set RPO/RTO, retention/deletion, destination, encryption/key custody,
   least-privilege access, backup operator, and rollback authority.
3. Authorize a narrow read-only MySQL eligibility assessment before selecting
   any MySQL backup method.
4. After that assessment, choose either a suitable MySQL-aware consistent
   snapshot approach or an approved quiesce/physical alternative.
5. Approve a maintenance/write-quiescence window before any MySQL backup.
6. Approve complete Kafka and InfluxDB preservation scope without authorizing
   Kafka recovery/startup.
7. Approve an isolated restore-test environment and accept its no-connect,
   no-consumer, no-notification, no-original-volume constraints.
8. Define acceptance criteria and decide who may authorize a primary rollback
   after a successful isolated test.
9. Confirm that Flyway, application startup, Kafka consumer processing,
   alerts/notifications/ML, and REFIT Task 4C remain separate decisions.

## Explicitly separate gates

The following remain outside any backup authorization:

- Kafka broker startup, OOM remediation, memory/JVM setting, topic/offset
  inspection, or consumer restart.
- User Service/Flyway startup or migration execution.
- Ingestion, Usage, Alert, Insight, ML, replay, telemetry, anomaly, mail, or
  notification processing.
- Keycloak restart, profile/device provisioning, or authentication changes.
- REFIT Task 4C deployment, credentials, household provisioning, or replay.

## Final decision

# NO-GO — BACKUP EXECUTION NOT AUTHORIZED until the required approvals and prerequisites are explicitly established.

The register identifies what must be decided, who must decide it by role, and
what evidence is required. It does not record any granted approval and does not
authorize backup creation, restoration, rollback, service recovery, or REFIT
work.

