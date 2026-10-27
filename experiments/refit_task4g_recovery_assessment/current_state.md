# Task 4G: Current State

## Audit scope

This assessment is read-only. It reviewed all six Task 4F reports, current Docker Engine/container metadata, non-secret Docker resource metadata, and repository configuration/source files. No Docker lifecycle command, HTTP request, database query, environment-variable inspection, secret extraction, or project-file change was performed.

## 1. Verified Docker state

| Item | Verified observation | Evidence |
|---|---|---|
| Docker Engine | Reachable; client and server are both version `29.7.2`. | Read-only `docker version` inspection. |
| Compose project | Existing application containers are labelled `home-energy-tracker` and reference the current `docker-compose.yml`. | Docker Compose labels from Task 4F and current inspection. |
| Running existing containers | `mysql` and `kafka-ui` only. | Current Docker container state. |
| MySQL | Running, restart policy `always`, Docker health status `healthy`. | Current Docker inspect metadata. |
| Kafka UI | Running, restart policy `unless-stopped`, no Docker health check. | Current Docker inspect metadata. |
| Kafka broker | Exited, exit `137`, `OOMKilled=true`, restart policy `no`. | Current Docker inspect metadata. |
| Other Home Energy Tracker services | Fifteen are exited, mostly exit `255`, restart policy `no`, no Docker state error, non-OOM. | Current Docker inspect metadata. |
| REFIT Task 4C | No container, `refit-task4c-network`, or REFIT Task 4C volume exists. | Current filtered read-only Docker checks. |

## 2. Current component state

| Component group | State | Recovery implication |
|---|---|---|
| MySQL | Running and healthcheck healthy | Existing persistent database remains live; do not recreate, reset, or point REFIT to it. |
| Kafka/Kafka UI | Broker stopped/OOM-killed; UI running but broker-degraded | No Kafka-dependent service is ready. The UI is not proof of broker availability. |
| Keycloak/API Gateway | Both stopped | Existing login and application ingress are unavailable. |
| User/Device services | Both stopped | Existing profile/device workflow is unavailable. |
| Ingestion/Usage services | Both stopped | Telemetry and usage pipelines are unavailable. |
| InfluxDB | Stopped | Existing time-series path is unavailable. |
| ML/Alert/Insight | Stopped | Model inference and downstream alert/insight processing are unavailable. |
| Frontend/monitoring/Mailpit | Stopped | UI, observation, and mail test infrastructure are unavailable. |

## 3. Interpretation of the stopped-container pattern

### Verified facts

- The fifteen non-Kafka Home Energy Tracker containers that are stopped have nearly identical finish timestamps around `2026-10-14T15:31:52Z`.
- Their Docker state shows exit `255`, `OOMKilled=false`, and no Docker `State.Error` text.
- Their restart policy is `no`; therefore Docker Engine restart would not automatically bring them back.
- `mysql` restarted because its policy is `always`; `kafka-ui` restarted because its policy is `unless-stopped`.

### Hypothesis, not a conclusion

The aligned exit time is consistent with a shared Docker Desktop/Engine or host lifecycle interruption. It does **not** prove the cause, and it does not establish that individual application services were healthy before the interruption.

### Verified separate blocker

Kafka was OOM-killed on `2026-10-11`, substantially before the shared exit-`255` pattern. It requires an independent recovery decision and must not be treated as part of the later Docker shutdown pattern.

## 4. Available diagnostic evidence

| Evidence source | What it establishes | Limitation |
|---|---|---|
| Task 4F reports | Baseline post-restart state, no REFIT resources, stopped stack, current volumes/networks/ports. | Does not prove root cause or application-level health. |
| Current Docker inspect state | Exact name, state, exit code, OOM flag, restart policy, start/finish times, and health where configured. | Does not expose application semantics or validate data integrity. |
| Compose configuration | Declared dependencies, restart policies, health checks, images, and persistent-volume intent. | Does not establish effective runtime environment values. |
| Redacted Kafka/MySQL/Kafka UI log categories | Existing persisted MySQL came ready; Kafka UI cannot reach stopped broker; no log signature proved Kafka's OOM cause. | Broad raw log review was intentionally avoided to protect credentials. |
| Docker Engine summary | Engine capacity and aggregate container count. | Aggregate count conflicts with direct enumeration and is not relied upon as the primary inventory. |

## 5. REFIT separation

REFIT Task 4C remains wholly separate and unstarted. The existing `home-energy-tracker_default` network, existing MySQL/Kafka/InfluxDB volumes, development Keycloak import, ports, and stopped application containers must not be reused for REFIT. Task 4E prerequisites remain independently unresolved.

## Current-state conclusion

Recovery planning can proceed, but recovery execution is **not safe to begin yet**. Kafka's broker-specific OOM issue, persistent-store safeguards, migration/initialization effects, consumer side effects, and approval gates require resolution first.
