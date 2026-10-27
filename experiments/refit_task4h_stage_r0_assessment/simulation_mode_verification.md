# Task 4H Stage R0 — Simulation, Replay, Alert, and Notification Verification

## Scope and decision boundary

This assessment inspected static configuration and source only. It did not inspect
container environment values, start a service, send telemetry, invoke a replay
helper, consume a Kafka record, call an endpoint, or trigger an alert/email.

A stopped container is a current runtime state, not proof that the corresponding
feature is permanently disabled.

## Finding labels

- **VERIFIED** — directly supported by static source/configuration or
  read-only runtime-resource evidence.
- **INFERRED** — a plausible behavior after a future start, not observed here.
- **UNRESOLVED** — effective runtime state was not safely established.
- **RECOMMENDED** — a future approval-gated control; it was not executed.

## Evidence reviewed

- Actual .env plus .env.example and .env.production.example, inspected only for
  the non-secret SIMULATION_ENABLED control classification.
- Ingestion application.properties and docker-compose.yml control references.
- ContinuousDataSimulator and ParallelDataSimulator source.
- Usage, Alert, Email, and ML Kafka-worker source.
- Task 4F/4G runtime and risk reports.
- Task 4H-FINAL read-only REFIT resource check.

## Control-state assessment

| Function | Classification | Static evidence | Stage R0 conclusion |
|---|---|---|---|
| Synthetic ingestion simulation | **VERIFIED** | Actual .env, .env.example, and .env.production.example each classify SIMULATION_ENABLED as explicit false. Ingestion application.properties and Compose also provide false fallbacks. | Static configuration is explicitly OFF. |
| Effective synthetic simulation at future runtime | **UNRESOLVED** | Container effective environment was not inspected and a later override can supersede static fallback values. | Do not claim permanent/runtime disable from a stopped container or a static file alone. |
| Continuous simulator activation | **VERIFIED** | ContinuousDataSimulator is conditional on simulation.enabled=true; its scheduler annotation is commented out. | It is conditional, but this does not control the parallel simulator. |
| Parallel simulator activation | **VERIFIED** | ParallelDataSimulator is conditional on simulation.enabled=true and contains scheduled random telemetry generation plus HTTP posting. | If effective simulation becomes true, telemetry can be generated. |
| Manual REFIT replay helper | **VERIFIED** | A real_data_replay/replay_stream.py helper exists in the repository. No helper execution occurred in Task 4H. | Presence of a manual tool is not evidence of an automatic replay or of a permanent replay-disable control. |
| Retained Kafka event processing | **UNRESOLVED** | Usage, Alert, and ML consumer paths exist; broker topics, consumer offsets, lag, and effective consumer runtime state were not inspected. | A future consumer start can process retained events; no replay-safety conclusion is justified. |
| Threshold alerts | **VERIFIED** | Usage Service consumes energy-usage, writes to InfluxDB, performs scheduled aggregation, and can publish energy-alerts when user conditions are met. | Future alert generation remains a side-effect risk. |
| Alert persistence and notification | **VERIFIED** | Alert Service consumes threshold/anomaly events, persists alerts, and attempts email delivery when an address is available. | There is no verified production-wide OFF control. |
| Production alert/listener disable | **UNRESOLVED** | Static scan found no production alert-disable, notification-disable, or listener-auto-startup=false control; listener-off settings found were test-only. | Alert/notification behavior after recovery remains unresolved. |
| Baseline ML event processing | **VERIFIED** | Primary Compose config enables baseline ML Kafka processing; main.py starts the legacy worker when enabled, and the worker consumes energy-usage then emits anomaly results/failure events. | A future ML start can produce events consumed by Alert Service. |
| Controlled REFIT branch | **VERIFIED** | Compose static defaults for controlled REFIT experiment and controlled Kafka worker are false, with separate controlled topics/groups in source. | Static isolation exists, but it is not a deployed runtime state. |
| Controlled REFIT effective state | **UNRESOLVED** | Source and Compose fallback behaviors are not identical; effective runtime values were not inspected. | Do not infer runtime disable from either fallback alone. |
| REFIT Task 4C deployment | **VERIFIED** | Task 4H-FINAL read-only Docker check found no matching Task 4C container, network, or volume. | No REFIT deployment/replay was created by Stage R0. |

## Source-level details

### Simulation

- **VERIFIED:** Ingestion application.properties and docker-compose.yml define
  false fallback behavior for SIMULATION_ENABLED.
- **VERIFIED:** ContinuousDataSimulator and ParallelDataSimulator use
  conditional activation based on simulation.enabled=true.
- **VERIFIED:** ParallelDataSimulator has a scheduled path that creates random
  telemetry and posts it to the ingestion interface when enabled.
- **INFERRED:** The static false values are a useful defense against accidental
  startup, but external environment or launch-time overrides can supersede
  them.
- **UNRESOLVED:** The effective environment of a future Ingestion container was
  intentionally not inspected.

### Replay and Kafka consumption

- **VERIFIED:** The repository includes a manually invoked replay helper and
  separate baseline/controlled Kafka worker paths.
- **VERIFIED:** Usage consumes energy-usage; Alert consumes energy-alerts and
  anomaly results; baseline ML can consume energy-usage and publish anomaly
  results.
- **INFERRED:** Retained records can lead to writes, anomaly results, alerts,
  and notifications after consumers start.
- **UNRESOLVED:** Topic retention, group offsets, lag, subscription startup
  state, and any externally supplied consumer setting. Auto-offset behavior in
  source is not a substitute for live group state.

### Alerts and notifications

- **VERIFIED:** Usage threshold logic runs on a schedule and can emit
  energy-alerts based on stored user alert conditions.
- **VERIFIED:** Alert Service persists events and can attempt mail delivery.
  Deduplication is suppression behavior, not a global feature disable.
- **UNRESOLVED:** Existing user alerting flags, thresholds, mailbox behavior,
  effective listener settings, and queued records.
- **RECOMMENDED:** Keep Usage, Alert, and ML stopped until Kafka backlog,
  user-level alert conditions, and notification behavior are separately
  assessed and authorized.

## Recommended safety gates

1. Before any Ingestion start, repeat non-secret effective-runtime verification
   of SIMULATION_ENABLED and preserve evidence that it is false.
2. Before any Usage, Alert, or ML start, assess retained records and
   consumer-group offsets under a separately approved, non-mutating procedure.
3. Before Alert start, explicitly approve the consequences of persisted alerts
   and possible Mailpit/email delivery.
4. Before ML start, explicitly approve anomaly processing and downstream Alert
   Service interaction.
5. Keep manual replay tooling unused and Task 4C undeployed until its separate
   provisioning and isolation prerequisites are approved.

## Stage R0 conclusion

**NO-GO for data-plane recovery.** Static simulation controls are explicitly
OFF, but effective future runtime values, retained-event replay behavior, alert
processing, notifications, and baseline ML side effects are not fully verified.
No service start or replay is authorized by this report.

