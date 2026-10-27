# Task 4F: Startup and Health Findings

## Audit boundary

No HTTP endpoint was called. Health conclusions are derived from Docker container state, Docker health status where present, restart policy metadata, and a minimal redacted log review. They are not application-level functional tests.

## 1. Existing application health

**Finding: the existing Home Energy Tracker application is not healthy end to end.**

| Required path element | State during audit | Consequence |
|---|---|---|
| MySQL | Running; Docker health status `healthy` | Existing database process is available, but this alone does not prove application health. |
| Kafka | Exited; exit code `137`; `OOMKilled=true`; finished on 2026-10-11 | Messaging-dependent services cannot be considered operational. |
| Kafka UI | Running | The UI is not evidence of broker health. Redacted log review showed it could not resolve/connect to `kafka:9092` while Kafka is stopped. |
| InfluxDB | Exited | Usage/time-series path is unavailable. |
| Keycloak | Exited | Existing interactive OIDC login path is unavailable. |
| API Gateway | Exited | No supported application ingress path is running. |
| User and Device services | Exited | Profile/device application APIs are unavailable. |
| Ingestion and Usage services | Exited | Telemetry/usage pipeline is unavailable. |
| Frontend | Exited | Existing UI is unavailable. |
| ML inference, Alert, Insight | Exited | These optional services are not running. |

No direct HTTP health endpoint was called because Task 4F prohibits requests. The finding above is sufficient to conclude that the system must not be treated as running or ready for REFIT work.

## 2. Common service stop pattern

Fifteen Home Energy Tracker containers, including Gateway, Keycloak, frontend, application services, InfluxDB, monitoring, Alert, and ML, show:

- state `exited`;
- exit code `255`;
- empty Docker `State.Error` metadata;
- `OOMKilled=false`; and
- nearly identical Docker finish timestamps around `2026-10-14T15:31:52Z`.

This common pattern is **consistent with** a shared Docker Desktop/Engine or host lifecycle interruption rather than separately proven application failures. It is not proof of the precise cause. Most of these services have restart policy `no`, so they did not resume when Docker became available again.

Kafka is different: it was OOM-killed earlier, on 2026-10-11. That is a concrete existing-stack blocker requiring a separately authorized diagnosis before any attempt to restore the existing stack.

## 3. Minimal redacted log observations

Only minimal logs required to distinguish an unexpected initialization from a stopped-dependency condition were reviewed. No raw credentials, token values, headers, or environment variables were inspected or recorded.

| Container | Redacted observation | Interpretation |
|---|---|---|
| `mysql` | Startup output indicated an existing persisted server reached ready state after the current Docker lifecycle event. | No fresh database initialization was observed in the selected output. This is not a database-integrity proof. |
| `kafka-ui` | Its broker hostname `kafka:9092` could not be resolved/reached while Kafka was stopped. | Kafka UI is operational as a container but degraded for its intended broker function. |
| Other exited Home Energy Tracker containers | State/exit metadata was sufficient; broad log collection was intentionally avoided. | No app-specific root cause is claimed from this audit. |

## 4. REFIT startup checks

| Check | Result |
|---|---|
| Task 4C container running/stopped/created | No container found. |
| Task 4C isolated network | Not found. |
| Task 4C isolated volumes | Not found. |
| REFIT persistence initialization | No Docker evidence. |
| REFIT profile/device/token creation | No Docker evidence; no request was made by this audit. |
| REFIT replay, event generator, ML, or alert execution | No Docker evidence of a Task 4C deployment; none was run by this audit. |

## 5. Health conclusion

Docker Engine running is not equivalent to a healthy application. The existing Home Energy Tracker stack is partially down, and its Kafka broker has an OOM termination record. REFIT remains prohibited until a separate approved recovery/diagnosis task resolves or explicitly isolates this existing-stack condition.
