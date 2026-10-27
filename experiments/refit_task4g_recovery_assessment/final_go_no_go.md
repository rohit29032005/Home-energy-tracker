# Final GO/NO-GO Decision — Task 4G

## Decision

# NO-GO — RECOVERY EXECUTION IS NOT YET AUTHORIZED

The read-only Task 4G assessment is complete. It is safe to prepare a staged
recovery plan, but it is **not** safe to start the existing Home Energy Tracker
yet. No Docker lifecycle action, HTTP request, application configuration
change, database action, REFIT deployment, or telemetry replay was performed.

## Basis for the decision

| ID | Verified fact or unresolved issue | Consequence | Required prerequisite before recovery execution |
|---|---|---|---|
| GO-01 | Kafka exited with OOMKilled=true and exit code 137; the exact resource/root cause is not proven. | Restarting it without a capacity plan can repeat failure or destabilize Docker Desktop. | Approved capacity diagnosis and broker-only recovery criteria. |
| GO-02 | Kafka retains persistent storage and several services consume/produce events. | Consumers can process historical events and create writes, anomalies, alerts, or notifications. | Approved topic/offset/backlog assessment and service-by-service authorization. |
| GO-03 | User Service enables Flyway against retained MySQL. | Startup can validate/apply migrations and affect existing records/schema. | Verified backup/rollback plus migration-history and pending-impact review. |
| GO-04 | InfluxDB and Keycloak retain/import state whose recovery behavior was not established. | Casual restart/recreation can introduce initialization or identity-state risk. | Service-specific persistence/init review and rollback approach. |
| GO-05 | Most Compose dependencies are service_started rather than health/readiness checks. | Bulk startup can race prerequisites and create misleading/inconsistent results. | Defined application-level readiness gates for each recovery stage. |
| GO-06 | Ingestion simulation is source-gated, but its effective runtime value was not inspected. | An unintended simulation setting can generate telemetry during recovery. | Non-secret verification that simulation is disabled. |
| GO-07 | Engine-level running-container aggregate differed from direct project-container inventory. | It does not prove damage, but is a diagnostic anomaly to reconcile in preflight. | Reconcile inventory before lifecycle actions. |
| GO-08 | Task 4G authorization is explicitly read-only. | No recovery action is inside current authorization. | Explicit user approval for narrowly scoped Stage R0 only. |

## Verified current distinction

- **Docker Engine:** Running and reachable.
- **Existing Home Energy Tracker:** Partially down. MySQL is running/healthy;
  Kafka UI is running; Kafka is stopped after OOM kill; other application
  services are stopped following the later Docker interruption.
- **REFIT Task 4C:** Not deployed. No REFIT Task 4C container, network, or
  volume was found. It remains independently gated.

## Minimum safe next approval

Authorize **Stage R0 only** from recovery_plan.md:

1. Preserve and protect existing persistent volumes.
2. Establish backup/rollback and migration-impact evidence.
3. Verify, without exposing secrets, that simulation is disabled.
4. Produce approved Kafka capacity/recovery criteria.
5. Define service readiness and abort evidence.

That approval would still **not** authorize Kafka start, User Service start,
full Compose startup, endpoint testing, data replay, REFIT provisioning, or
any consumer/alert/ML processing.

## Conditions for a future conditional GO

A later recovery review can issue a conditional GO only after R0 evidence is
accepted and the user explicitly authorizes a **Kafka broker-only** recovery
stage. Each later stage needs separate confirmation because it can introduce
database, event-processing, notification, identity, or telemetry side effects.

## Stop condition met

Task 4G stops here. The reports document evidence, risks, and the proposed
staged recovery sequence; no recovery-plan step has been executed.

