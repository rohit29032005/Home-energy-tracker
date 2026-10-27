# Task 4H Stage R0 — Recovery Prerequisites and Approval Gates

## Scope and decision boundary

This report converts Stage R0 evidence into explicit preconditions for a future
existing-stack recovery review. It is not permission to start, restart, create,
or reconfigure any service.

Status terms:
- **VERIFIED**: supported by read-only Docker/source/report evidence.
- **INFERRED**: plausible consequence, not directly observed at runtime.
- **UNRESOLVED**: evidence is insufficient or prohibited to obtain in Stage R0.
- **RECOMMENDED**: future approval-gated control.

## Required prerequisite register

| ID | Prerequisite | Current status | Evidence | Required approval / owner |
|---|---|---|---|---|
| P-01 | Preserve existing persistent volumes and forbid destructive cleanup. | **VERIFIED inventory; gate OPEN** | Task 4F/4G identify MySQL, Kafka, InfluxDB, Grafana, and Prometheus persistent volumes. | Explicit project-owner approval for any volume-related operation. |
| P-02 | Consistent backup and isolated restore/rollback test. | **UNRESOLVED** | No backup, artifact verification, or restore test was performed; see backup_rollback_plan.md. | Explicit maintenance/backup approval and qualified recovery operator. |
| P-03 | Kafka OOM root-cause/capacity evidence and broker-only plan. | **UNRESOLVED** | OOMKilled=true is verified; safe memory/JVM configuration is not justified; see kafka_capacity_assessment.md. | Explicit Kafka broker-only assessment approval. |
| P-04 | Kafka retained-topic, consumer-group, offset, and backlog side-effect assessment. | **UNRESOLVED** | Persistent Kafka state and downstream consumers exist; live topic/group state was not inspected. | Explicit event-processing/recovery approval. |
| P-05 | Flyway history, pending migration, checksum, and schema compatibility review. | **UNRESOLVED** | User Service enables Flyway; static migration risk is known; live DB history was not queried; see flyway_migration_impact.md. | Explicit read-only database assessment approval after backup gate. |
| P-06 | Effective simulator safety confirmation. | **VERIFIED static OFF; runtime gate OPEN** | Actual .env and static fallbacks are false, but effective future container environment is unverified; see simulation_mode_verification.md. | Explicit non-secret runtime configuration review before Ingestion start. |
| P-07 | Replay/consumer safety. | **UNRESOLVED** | Manual replay tooling and consumer paths exist; offset/lag state unknown. | Explicit no-replay/no-consumer plan and event-processing approval. |
| P-08 | Alerts, notifications, and ML anomaly side-effect control. | **UNRESOLVED** | Usage can publish alerts; Alert can persist/send; ML can publish anomalies. | Explicit approval for alert/mail/anomaly consequences. |
| P-09 | InfluxDB persistence/init behavior. | **UNRESOLVED** | Existing data volume plus configuration mount; current init state not inspected. | Explicit storage/init review and rollback protection. |
| P-10 | Keycloak identity persistence/import behavior. | **UNRESOLVED** | Development import mount exists; no declared named identity DB volume. | Explicit identity-recovery review. |
| P-11 | Application readiness criteria beyond Compose ordering. | **UNRESOLVED** | Most dependencies are service_started rather than health checks. | Approval for stage-specific non-secret readiness verification. |
| P-12 | REFIT Task 4C isolation. | **VERIFIED** | Current Task 4H-FINAL read-only check found no Task 4C container, network, or volume. | Keep separate gate; no existing-stack recovery approval covers REFIT. |

## Verified service dependency and risk facts

- **VERIFIED:** MySQL is running/healthy at Docker level. Kafka UI is running but
  does not prove broker readiness. Kafka is stopped after OOM.
- **VERIFIED:** User Service and Device Service depend on MySQL; Ingestion,
  Usage, Alert, and ML have Kafka-related dependencies; Usage also depends on
  InfluxDB; Gateway depends on core services and Keycloak.
- **VERIFIED:** User Service Flyway can introduce schema/data changes. Usage,
  Alert, and ML can process events and create writes, alerts, anomalies, or
  notifications.
- **INFERRED:** Starting the full Compose project can race readiness and
  unintentionally activate multiple initialization/event paths.
- **RECOMMENDED:** Never use broad project-wide Compose startup as a recovery
  shortcut.

Supporting evidence: Task 4G service_dependency_map.md and
data_and_initialization_risks.md.

## Recommended staged order for a future recovery review

This order is **RECOMMENDED**, not executed.

1. **R0 protection:** Accept P-01 through P-12 evidence and decide backup,
   rollback, migration, and side-effect authority.
2. **R1 Kafka only:** After P-02/P-03/P-04 approval, start only the exact
   existing Kafka broker under a broker-only observation plan. Keep consumers
   stopped.
3. **R2 independent dependencies:** Retain healthy MySQL. Assess/recover
   InfluxDB, Keycloak, and Mailpit separately only after their persistence/init
   gates are accepted.
4. **R3 control plane:** Start User Service only after Flyway gate acceptance,
   then Device Service after User Service readiness.
5. **R4 data plane:** Consider Ingestion only after simulator confirmation;
   Usage, Alert, Insight, and ML each require their own event/notification
   approvals.
6. **R5 access/monitoring:** Gateway after required dependencies and Keycloak;
   frontend and monitoring last.

## Required readiness evidence for a future stage

| Service group | Minimum future readiness criterion | Current Stage R0 state |
|---|---|---|
| MySQL | Docker health plus approved database/migration consistency evidence. | Docker healthy only; application/migration consistency unverified. |
| Kafka | Broker-only stability, capacity within approved budget, persistent-log recovery evidence, and no-consumer gate. | Not established. |
| InfluxDB | Existing-volume/init behavior and declared health criterion after approved start. | Not established. |
| Keycloak | Identity/import persistence behavior and approved login/token validation plan. | Not established. |
| User/Device | User Flyway outcome and application readiness before Device starts. | Not established. |
| Ingestion/Usage/Alert/ML | Simulator, consumer backlog, writes, anomalies, alert, and mail gates accepted. | Not established. |
| Gateway/frontend/monitoring | All mandatory dependencies have demonstrated readiness; endpoint checks separately approved. | Not established. |

## Data-initialization risk gates

| Risk | Classification | Required control |
|---|---|---|
| Flyway schema/seed migration | **VERIFIED risk** | Backup plus approved history/pending-migration assessment. |
| Kafka retained events | **VERIFIED risk** | Consumer offset/backlog review and no-consumer gate. |
| InfluxDB initialization | **UNRESOLVED** | Existing data/configuration state protection and init behavior review. |
| Keycloak realm/import behavior | **UNRESOLVED** | Separate identity persistence/recovery plan. |
| Synthetic telemetry | **VERIFIED static control; runtime UNRESOLVED** | Effective simulation verification before any Ingestion start. |
| Alerts/emails/anomalies | **VERIFIED code path; runtime UNRESOLVED** | Explicit side-effect authorization before consumer start. |

## Stage R0 decision

All critical gates remain open. **NO-GO for recovery execution.** The next
possible decision is a human review of this evidence, followed only by a
narrowly approved preflight or broker-only stage. REFIT Task 4C remains isolated
and separately gated.

